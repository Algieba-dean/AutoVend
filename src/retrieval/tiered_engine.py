"""
Agile, Tiered, Low-Latency RAG Engine (src/retrieval/tiered_engine.py).

Provides a 3-tier adaptive retrieval architecture:
- Tier 0 / Fast-Path (< 1-2 ms): In-memory exact spec / tabular entity lookup and
  semantic cache for direct spec queries (e.g., "SU7 Max 零百加速是多少", "小米电机转速是多少").
  Returns grounded facts in < 1-2 ms without invoking expensive embedding models or cross-encoders.
- Tier 1: Agile single-shot hybrid BM25 + dense retrieval for targeted informational queries.
- Tier 2: Deep multi-angle parent-child retrieval for complex comparative or multi-document reasoning.
- Dynamic context compression and minimal prompt budgeting to maximize generation speed and reduce TTFT.
"""

import logging
import re
import threading
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

from src.core.terminology import AutomotiveKnowledgeGraph
from src.filter.vehicle_db import VehicleDB

logger = logging.getLogger(__name__)


# -------------------------------------------------------------------------
# Tier 0 In-Memory Fast-Path Indices & Caches
# -------------------------------------------------------------------------

SPEC_ATTRIBUTE_PATTERNS: List[Tuple[re.Pattern, str, str]] = [
    (re.compile(r"零百|百公里加速|0-100|几秒破百|加速"), "acceleration_0_100", "0-100km/h加速"),
    (re.compile(r"极速|最高时速|最高车速|能跑多快"), "max_speed", "最高车速"),
    (re.compile(r"纯电续航|综合续航|续航里程|续航|能跑多少公里|cltc"), "electric_range", "CLTC续航里程"),
    (re.compile(r"电池(?:容量|大小|包|品牌|厂家|厂商|供应商|类型|安全)?|多少度电|度电|电芯|三元锂|磷酸铁锂|麒麟电池|神行电池|刀片电池"), "battery_capacity", "电池规格与品牌"),
    (re.compile(r"官方指导价|指导价|售价|价格|多少钱|多少万|落地价|预算"), "prize", "官方指导价"),
    (re.compile(r"马力|功率|多少匹|输出功率"), "horsepower", "最大马力"),
    (re.compile(r"扭矩|峰值扭矩"), "torque", "峰值扭矩"),
    (re.compile(r"电机转速|转速|转/分|rpm|双电机|单电机|电机"), "motor_tech", "电机动力科技"),
    (re.compile(r"轴距|车长|车宽|车高|长宽高|尺寸"), "wheelbase", "轴距/车身尺寸"),
    (re.compile(r"几座|座位|座椅布局|5座|6座|7座"), "seat_layout", "座椅布局"),
    (re.compile(r"驱动|四驱|后驱|两驱|前驱"), "drive_type", "驱动形式"),
    (re.compile(r"动力形式|纯电|插混|增程|油电混动|油车"), "powertrain_type", "动力类型"),
    (re.compile(r"后备箱|行李箱容积|储物空间"), "cargo_volume", "后备箱容积"),
    (re.compile(r"智驾|辅助驾驶|自动驾驶|算力|芯片|激光雷达|orin"), "autonomous_driving_level", "智能驾驶级别"),
    (re.compile(r"快充|800v|高压平台|充电速度|超充|充满要多久|充电要多久"), "charging_tech", "高压超快充架构"),
]


class SemanticQueryCache:
    """Thread-safe LRU in-memory query cache for sub-millisecond retrieval hits."""

    def __init__(self, capacity: int = 1000):
        self.capacity = capacity
        self._cache: OrderedDict[str, Any] = OrderedDict()
        self._lock = threading.RLock()

    def _normalize_key(self, query: str) -> str:
        q = query.lower().strip()
        q = re.sub(r"[\s\?\!\,\.\;\:\'\"\(\)\-\_，。？！]+", "", q)
        return q

    def get(self, query: str) -> Optional[Any]:
        key = self._normalize_key(query)
        if not key:
            return None
        with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)
                return self._cache[key]
            return None

    def put(self, query: str, value: Any) -> None:
        key = self._normalize_key(query)
        if not key:
            return
        with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)
            self._cache[key] = value
            if len(self._cache) > self.capacity:
                self._cache.popitem(last=False)

    def clear(self) -> None:
        with self._lock:
            self._cache.clear()


@dataclass
class TieredSearchResult:
    """Result of tiered retrieval execution."""

    tier: int  # 0, 1, or 2
    is_fast_path: bool
    latency_ms: float
    results: List[Any] = field(default_factory=list)
    facts_summary: str = ""
    candidate_count: int = 0
    routing_reason: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


ENTERPRISE_FLAGSHIP_SPECS: Dict[str, Dict[str, Any]] = {
    "小米-SU7 Max": {
        "car_model": "小米-SU7 Max",
        "brand": "小米",
        "prize": "29.99万元",
        "vehicle_category_bottom": "中大型纯电轿跑",
        "powertrain_type": "纯电动",
        "drive_type": "双电机全轮驱动 (AWD)",
        "seat_layout": "5座",
        "acceleration_0_100": "2.78秒",
        "max_speed": "265km/h",
        "electric_range": "800km (CLTC)",
        "battery_capacity": "101kWh三元锂麒麟电池",
        "horsepower": "673马力 (495kW)",
        "torque": "838N·m",
        "wheelbase": "3000mm",
        "motor_tech": "小米HyperEngine V6s超高效双电机 (转速高达21,000rpm，V8s电机可达27,200rpm)",
        "charging_tech": "全栈871V真800V高压碳化硅平台 (15分钟充电补能510km)",
        "autonomous_driving_level": "Xiaomi Pilot Max (双Orin-X 508TOPS + 激光雷达)",
    },
    "小米-SU7 Pro": {
        "car_model": "小米-SU7 Pro",
        "brand": "小米",
        "prize": "24.59万元",
        "vehicle_category_bottom": "中大型纯电轿跑",
        "powertrain_type": "纯电动",
        "drive_type": "单电机后驱 (RWD)",
        "seat_layout": "5座",
        "acceleration_0_100": "5.7秒",
        "max_speed": "210km/h",
        "electric_range": "830km (CLTC)",
        "battery_capacity": "94.3kWh神行超充电池",
        "horsepower": "299马力 (220kW)",
        "torque": "400N·m",
        "wheelbase": "3000mm",
        "motor_tech": "小米HyperEngine V6电机 (转速21,000rpm)",
        "charging_tech": "全域高压快充平台",
        "autonomous_driving_level": "Xiaomi Pilot Max (双Orin-X + 激光雷达)",
    },
    "小米-SU7 标准版": {
        "car_model": "小米-SU7 标准版",
        "brand": "小米",
        "prize": "21.59万元",
        "vehicle_category_bottom": "中大型纯电轿跑",
        "powertrain_type": "纯电动",
        "drive_type": "单电机后驱 (RWD)",
        "seat_layout": "5座",
        "acceleration_0_100": "5.28秒",
        "max_speed": "210km/h",
        "electric_range": "700km (CLTC)",
        "battery_capacity": "73.6kWh磷酸铁锂刀片电池",
        "horsepower": "299马力 (220kW)",
        "torque": "400N·m",
        "wheelbase": "3000mm",
        "motor_tech": "小米HyperEngine V6电机 (转速21,000rpm)",
        "charging_tech": "全域碳化硅快充平台",
        "autonomous_driving_level": "Xiaomi Pilot Pro (单Orin-N 84TOPS)",
    },
    "极氪-001": {
        "car_model": "极氪-001",
        "brand": "极氪",
        "prize": "26.90-32.90万元",
        "vehicle_category_bottom": "中大型豪华猎装轿跑",
        "powertrain_type": "纯电动",
        "drive_type": "双电机四驱 / 单电机后驱",
        "seat_layout": "5座",
        "acceleration_0_100": "3.3秒",
        "max_speed": "240km/h",
        "electric_range": "705-750km (CLTC)",
        "battery_capacity": "95kWh神行电池 / 100kWh麒麟电池",
        "horsepower": "789马力 (580kW)",
        "torque": "810N·m",
        "wheelbase": "3005mm",
        "motor_tech": "全栈800V碳化硅高性能电机",
        "charging_tech": "全栈800V超快充 (神行电池充电10.5分钟10%-80%)",
        "autonomous_driving_level": "浩瀚智驾 2.0 (双Orin-X + 激光雷达)",
    },
    "特斯拉-Model 3": {
        "car_model": "特斯拉-Model 3",
        "brand": "特斯拉",
        "prize": "23.19-27.19万元",
        "vehicle_category_bottom": "中型纯电轿车",
        "powertrain_type": "纯电动",
        "drive_type": "后轮驱动 / 全轮驱动",
        "seat_layout": "5座",
        "acceleration_0_100": "4.4秒",
        "max_speed": "200km/h",
        "electric_range": "606-713km (CLTC)",
        "battery_capacity": "60kWh / 78.4kWh",
        "horsepower": "264-450马力",
        "torque": "340-559N·m",
        "wheelbase": "2875mm",
        "motor_tech": "永磁同步电机",
        "charging_tech": "V3/V4超充桩最高250kW峰值功率",
        "autonomous_driving_level": "Autopilot / FSD (Hardware 4.0)",
    },
    "特斯拉-Model Y": {
        "car_model": "特斯拉-Model Y",
        "brand": "特斯拉",
        "prize": "24.99-35.49万元",
        "vehicle_category_bottom": "中型纯电SUV",
        "powertrain_type": "纯电动",
        "drive_type": "双电机全轮驱动 / 单电机后驱",
        "seat_layout": "5座",
        "acceleration_0_100": "3.7秒",
        "max_speed": "217km/h",
        "electric_range": "554-688km (CLTC)",
        "battery_capacity": "60kWh / 78.4kWh",
        "horsepower": "299-486马力",
        "torque": "440-659N·m",
        "wheelbase": "2890mm",
        "motor_tech": "高效双电机全轮驱动",
        "charging_tech": "V3超级充电",
        "autonomous_driving_level": "Autopilot / FSD (Hardware 4.0)",
    },
    "蔚来-ES6": {
        "car_model": "蔚来-ES6",
        "brand": "蔚来",
        "prize": "33.80-39.60万元",
        "vehicle_category_bottom": "中型纯电豪华SUV",
        "powertrain_type": "纯电动",
        "drive_type": "双电机智能四驱",
        "seat_layout": "5座",
        "acceleration_0_100": "4.5秒",
        "max_speed": "200km/h",
        "electric_range": "500-625km (CLTC)",
        "battery_capacity": "75kWh / 100kWh (支持可充可换可升级)",
        "horsepower": "490马力 (360kW)",
        "torque": "700N·m",
        "wheelbase": "2915mm",
        "motor_tech": "前150kW感应后210kW永磁高效双电机",
        "charging_tech": "全场景换电 + 高压超快充 (3分钟全自动换电)",
        "autonomous_driving_level": "Banyan系统 / 4颗Orin-X (1016TOPS)",
    },
    "比亚迪-汉EV": {
        "car_model": "比亚迪-汉EV",
        "brand": "比亚迪",
        "prize": "17.98-24.98万元",
        "vehicle_category_bottom": "中大型纯电轿车",
        "powertrain_type": "纯电动",
        "drive_type": "前驱 / 超级智能电四驱",
        "seat_layout": "5座",
        "acceleration_0_100": "3.9秒",
        "max_speed": "185km/h",
        "electric_range": "506-701km (CLTC)",
        "battery_capacity": "60.48-85.4kWh高安全超级刀片电池",
        "horsepower": "204-517马力",
        "torque": "310-700N·m",
        "wheelbase": "2920mm",
        "motor_tech": "宽温域高效热泵电驱动系统",
        "charging_tech": "全铝合金底盘与全车双枪超充",
        "autonomous_driving_level": "DiPilot 100 (天神之眼高阶智能驾驶辅助)",
    },
    "理想-L7": {
        "car_model": "理想-L7",
        "brand": "理想",
        "prize": "30.18-35.98万元",
        "vehicle_category_bottom": "中大型豪华增程SUV",
        "powertrain_type": "增程式混动",
        "drive_type": "双电机智能四驱",
        "seat_layout": "5座",
        "acceleration_0_100": "5.3秒",
        "max_speed": "180km/h",
        "electric_range": "225-286km (CLTC纯电) / 1360-1421km (综合续航)",
        "battery_capacity": "42.8kWh / 52.3kWh三元锂电池",
        "horsepower": "449马力 (330kW)",
        "torque": "620N·m",
        "wheelbase": "3005mm",
        "motor_tech": "前后双电机高效增程驱动 + 1.5T四缸增程器",
        "charging_tech": "高压快充 (20%-80%需30分钟)",
        "autonomous_driving_level": "AD Max (双Orin-X 508TOPS + 禾赛AT128激光雷达)",
    },
    "问界-M7": {
        "car_model": "问界-M7",
        "brand": "问界",
        "prize": "24.98-32.98万元",
        "vehicle_category_bottom": "中大型增程SUV",
        "powertrain_type": "增程式混动",
        "drive_type": "双电机四驱 / 单电机后驱",
        "seat_layout": "5座 / 6座",
        "acceleration_0_100": "4.8秒",
        "max_speed": "190km/h",
        "electric_range": "210-240km (CLTC纯电) / 1150-1300km (综合续航)",
        "battery_capacity": "40kWh三元锂/磷酸铁锂电池",
        "horsepower": "449马力 (330kW)",
        "torque": "660N·m",
        "wheelbase": "2820mm",
        "motor_tech": "华为DriveONE高效纯电驱增程平台",
        "charging_tech": "快速直流补能",
        "autonomous_driving_level": "HUAWEI ADS 2.0 / 3.0 高阶智能驾驶系统",
    },
    "比亚迪-汉DM-i": {
        "car_model": "比亚迪-汉DM-i",
        "brand": "比亚迪",
        "prize": "16.58-22.58万元",
        "vehicle_category_bottom": "中大型插电混动轿车",
        "powertrain_type": "插电式混合动力 (PHEV)",
        "drive_type": "前置前驱",
        "seat_layout": "5座",
        "acceleration_0_100": "7.9秒",
        "max_speed": "185km/h",
        "electric_range": "125-200km (CLTC纯电) / 1260-1350km (综合续航)",
        "battery_capacity": "18.3-30.7kWh专用功率型超安全刀片电池",
        "horsepower": "197-218马力",
        "torque": "315-325N·m",
        "wheelbase": "2920mm",
        "motor_tech": "DM-i超级混动专用E-CVT电驱动系统 + 骁云1.5T高热效率发动机",
        "charging_tech": "双枪快充 / 直流快充",
        "autonomous_driving_level": "DiPilot 智能驾驶辅助系统",
    },
}


class FastSpecIndex:
    """
    In-memory indexed vehicle specifications and OEM technology facts.
    Enables sub-millisecond grounded spec lookup without database or vector queries.
    """

    _instance: Optional["FastSpecIndex"] = None

    def __init__(self, db: Optional[VehicleDB] = None):
        self.db = db or VehicleDB()
        self.db_records: Dict[str, Dict[str, Any]] = {}
        self.normalized_models: Dict[str, str] = {}  # alias -> canonical car_model
        self.known_brands: Set[str] = set()
        self.kg = AutomotiveKnowledgeGraph.get_instance()
        self._build_index()

    @classmethod
    def get_instance(cls, db: Optional[VehicleDB] = None) -> "FastSpecIndex":
        if cls._instance is None:
            cls._instance = cls(db=db)
        return cls._instance

    def _build_index(self) -> None:
        """Load vehicle rows into memory and create alias mapping."""
        # Seed with enterprise flagship specs first
        for model, rec in ENTERPRISE_FLAGSHIP_SPECS.items():
            self.db_records[model] = dict(rec)
            if rec.get("brand"):
                self.known_brands.add(rec["brand"].lower())

        try:
            models = self.db.get_all_car_models()
        except Exception as e:
            logger.warning(f"Failed to fetch car models from DB: {e}")
            models = []

        for model in models:
            rec = self.db.get_by_model(model)
            if not rec:
                continue
            self.db_records[model] = rec

            brand = rec.get("brand", "")
            if brand:
                self.known_brands.add(brand.lower())

        # Build alias map across all records
        for model in self.db_records.keys():
            clean_model = model.lower().strip()
            self.normalized_models[clean_model] = model
            self.normalized_models[clean_model.replace(" ", "")] = model
            self.normalized_models[clean_model.replace("-", " ")] = model
            self.normalized_models[clean_model.replace("-", "")] = model

            if "-" in model:
                parts = model.split("-", 1)
                sub_name = parts[1].lower().strip()
                self.normalized_models[sub_name] = model
                self.normalized_models[sub_name.replace(" ", "")] = model

        # Popular aliases
        aliases = {
            "su7": "小米-SU7 标准版",
            "su7 max": "小米-SU7 Max",
            "su7 pro": "小米-SU7 Pro",
            "小米su7": "小米-SU7 标准版",
            "小米su7 max": "小米-SU7 Max",
            "极氪001": "极氪-001",
            "001": "极氪-001",
            "model 3": "特斯拉-Model 3",
            "model3": "特斯拉-Model 3",
            "model y": "特斯拉-Model Y",
            "modely": "特斯拉-Model Y",
            "蔚来es6": "蔚来-ES6",
            "es6": "蔚来-ES6",
            "比亚迪汉": "比亚迪-汉EV",
            "问界m7": "问界-M7",
            "理想l7": "理想-L7",
        }
        for alias, target in aliases.items():
            if target in self.db_records:
                self.normalized_models[alias] = target
                self.normalized_models[alias.replace(" ", "")] = target
            elif any(target.lower() in m.lower() for m in self.db_records):
                matched = next(m for m in self.db_records if target.lower() in m.lower())
                self.normalized_models[alias] = matched
                self.normalized_models[alias.replace(" ", "")] = matched

    def match_all_vehicle_models(self, query: str) -> List[str]:
        """Find all distinct canonical car models mentioned in user query text without substring collisions."""
        q_lower = query.lower()
        matched_spans: List[Tuple[int, int, str]] = []  # (start, end, canonical)

        # Sort keys by length descending to match longest specific name first (e.g. "su7 max" before "su7")
        for key in sorted(self.normalized_models.keys(), key=len, reverse=True):
            if len(key) < 2:
                continue
            idx = 0
            while True:
                pos = q_lower.find(key, idx)
                if pos == -1:
                    break
                end = pos + len(key)
                idx = pos + 1
                # Check if this span overlaps with an already matched longer span
                if any(not (end <= s or pos >= e) for s, e, _ in matched_spans):
                    continue
                canonical = self.normalized_models[key]
                matched_spans.append((pos, end, canonical))

        # Sort matched models by their appearance order in query
        matched_spans.sort(key=lambda x: x[0])
        result = []
        for _, _, c in matched_spans:
            if c not in result:
                result.append(c)
        return result

    def match_vehicle_model(self, query: str) -> Optional[str]:
        """Find canonical car model name from user query text."""
        models = self.match_all_vehicle_models(query)
        return models[0] if models else None

    def match_spec_attribute(self, query: str) -> Optional[Tuple[str, str]]:
        """Identify requested spec attribute from query text. Returns (field_name, display_label)."""
        for pattern, field_name, label in SPEC_ATTRIBUTE_PATTERNS:
            if pattern.search(query):
                return field_name, label
        return None

    def lookup_exact_spec(
        self, car_model: str, field_name: str
    ) -> Optional[Tuple[str, str, Dict[str, Any]]]:
        """
        Exact in-memory lookup of a vehicle attribute or related OEM technology.
        Returns (display_label, value_str, full_record).
        """
        rec = self.db_records.get(car_model)
        if not rec:
            return None

        # Check direct vehicle DB attributes
        if field_name in rec and rec[field_name]:
            val = rec[field_name]
            label = next(
                (lbl for pat, fn, lbl in SPEC_ATTRIBUTE_PATTERNS if fn == field_name), field_name
            )
            return label, str(val), rec

        # Check motor tech or charging tech via Knowledge Graph
        if field_name in ("motor_tech", "charging_tech"):
            veh_techs = self.kg.get_vehicle_technologies(car_model)
            if not veh_techs and rec.get("brand"):
                veh_techs = self.kg.get_brand_technologies(rec.get("brand"))

            if field_name == "motor_tech":
                motor_techs = [
                    t
                    for t in veh_techs
                    if "电机" in t.name or "转速" in t.summary or "HyperEngine" in t.name
                ]
                if motor_techs:
                    t = motor_techs[0]
                    return "电机核心科技", f"{t.name}: {t.summary}", rec
            elif field_name == "charging_tech":
                charge_techs = [
                    t
                    for t in veh_techs
                    if "800V" in t.name or "充电" in t.name or "碳化硅" in t.name
                ]
                if charge_techs:
                    t = charge_techs[0]
                    return "高压超充架构", f"{t.name}: {t.summary}", rec

        return None


# -------------------------------------------------------------------------
# Tiered Retrieval Engine
# -------------------------------------------------------------------------


class TieredRetrievalEngine:
    """
    Tiered Low-Latency Retrieval Engine.

    Routes queries through:
    - Tier 0: Direct Spec & Entity Lookup (< 1-2 ms)
    - Tier 1: Agile Single-Shot BM25 + Dense Hybrid Retrieval
    - Tier 2: Deep Multi-Angle Parent-Child Retrieval
    """

    _instance: Optional["TieredRetrievalEngine"] = None
    _lock = threading.RLock()
    _shared_cache = SemanticQueryCache(capacity=1000)

    def __init__(
        self,
        db: Optional[VehicleDB] = None,
        hybrid_pipeline: Optional[Any] = None,
        parent_child_retriever: Optional[Any] = None,
    ):
        self.fast_index = FastSpecIndex.get_instance(db=db)
        self.db = db or self.fast_index.db or VehicleDB()
        self.hybrid_pipeline = hybrid_pipeline
        self.parent_child_retriever = parent_child_retriever
        self.cache = self._shared_cache

    @classmethod
    def get_instance(
        cls,
        db: Optional[VehicleDB] = None,
        hybrid_pipeline: Optional[Any] = None,
        parent_child_retriever: Optional[Any] = None,
    ) -> "TieredRetrievalEngine":
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls(
                    db=db,
                    hybrid_pipeline=hybrid_pipeline,
                    parent_child_retriever=parent_child_retriever,
                )
            else:
                if hybrid_pipeline is not None and cls._instance.hybrid_pipeline is None:
                    cls._instance.hybrid_pipeline = hybrid_pipeline
                if (
                    parent_child_retriever is not None
                    and cls._instance.parent_child_retriever is None
                ):
                    cls._instance.parent_child_retriever = parent_child_retriever
            return cls._instance

    def is_tier0_candidate(self, query: str) -> bool:
        """Check if query is a candidate for Tier 0 fast-path retrieval."""
        models = self.fast_index.match_all_vehicle_models(query)
        if len(models) >= 2:
            # If query asks for deep qualitative reasoning (trade-offs, architectures, subjective comparisons),
            # dispatch to Tier 2 instead of tabular spec comparison
            deep_reasoning_clues = ["优缺点", "方案", "差异", "评价", "感受", "如何选择", "口碑", "深度", "长短处", "哪个好", "选哪个"]
            if any(k in query for k in deep_reasoning_clues):
                return False

            # Multi-vehicle fast-path comparison candidate if all mentioned cars have known specs
            # and a specific attribute is queried
            attr = self.fast_index.match_spec_attribute(query)
            all_known = all(m in self.fast_index.db_records for m in models)
            if attr and all_known:
                return True
            return False

        # Single vehicle spec lookup
        if len(models) == 1:
            attr = self.fast_index.match_spec_attribute(query)
            if attr:
                return True

        # Check if query asks for a direct proprietary technology entity (e.g. "小米电机转速是多少")
        matched_terms = self.fast_index.kg.extract_terms(query)
        if matched_terms and any(
            re.search(r"转速|多少|参数|原理|架构|功率|多大|几秒|容量|快充", query) for _ in [1]
        ):
            return True

        return False

    def is_tier2_candidate(self, query: str) -> bool:
        """Check if query requires Tier 2 deep multi-angle or parent-child retrieval."""
        comparative_indicators = [
            "对比",
            "相比",
            "差别",
            "不同",
            "优势和缺点",
            "优缺点",
            "横评",
            "比一比",
            "更推荐哪个",
            "哪个更好",
            "哪个好",
            "选哪个",
            "vs",
            "versus",
            "pk",
        ]
        q_lower = query.lower()
        has_comparison = any(ind in q_lower for ind in comparative_indicators)
        models = self.fast_index.match_all_vehicle_models(query)
        return has_comparison or (len(models) >= 2)

    def search_tier0(
        self, query: str, car_model_hint: Optional[str] = None
    ) -> Optional[TieredSearchResult]:
        """
        Execute Tier 0 In-Memory Fast-Path Lookup (< 1-2 ms).
        Supports single vehicle spec query and multi-vehicle side-by-side spec comparison.
        """
        start = time.perf_counter()

        # Check semantic cache first (use compound key if hint provided)
        cache_key = f"{query}::{car_model_hint}" if car_model_hint else query
        cached = self.cache.get(cache_key)
        if cached is not None:
            latency_ms = (time.perf_counter() - start) * 1000.0
            return TieredSearchResult(
                tier=0,
                is_fast_path=True,
                latency_ms=round(latency_ms, 3),
                results=cached.results,
                facts_summary=cached.facts_summary,
                candidate_count=len(cached.results),
                routing_reason="Tier 0 Cache Hit (内存语义缓存命中)",
                metadata={"cache_hit": True},
            )

        models = self.fast_index.match_all_vehicle_models(query)
        spec_attr = self.fast_index.match_spec_attribute(query)

        # ── Case A: Multi-vehicle fast-path tabular comparison (< 2ms) ──────────
        if len(models) >= 2:
            results = []
            facts_lines = ["【车型规格横向对比】"]
            comparison_highlights = []

            for m in models:
                rec = self.fast_index.db_records.get(m)
                if not rec:
                    continue
                brand = rec.get("brand", "")
                price = rec.get("prize", "")
                category = rec.get("vehicle_category_bottom", "")
                powertrain = rec.get("powertrain_type", "")
                acc = rec.get("acceleration_0_100", "")
                rng = rec.get("electric_range", "")

                line = f"- {m}: 官方指导价 {price} | 0-100km/h加速: {acc} | 续航: {rng}"
                if spec_attr:
                    lookup_res = self.fast_index.lookup_exact_spec(m, spec_attr[0])
                    if lookup_res:
                        comparison_highlights.append(f"{m} ({lookup_res[1]})")
                facts_lines.append(line)

                from src.rag_service.schemas import VehicleSearchResult

                results.append(
                    VehicleSearchResult(
                        car_model=m,
                        score=1.0,
                        brand=brand,
                        price=price,
                        category=category,
                        powertrain_type=powertrain,
                        metadata=rec,
                        text_snippet=line,
                    )
                )

            if results:
                if spec_attr and comparison_highlights:
                    facts_lines.append(
                        f"👉 重点对比项【{spec_attr[1]}】: {' vs '.join(comparison_highlights)}"
                    )

                facts_text = "\n".join(facts_lines)
                latency_ms = (time.perf_counter() - start) * 1000.0
                final_res = TieredSearchResult(
                    tier=0,
                    is_fast_path=True,
                    latency_ms=round(latency_ms, 3),
                    results=results,
                    facts_summary=facts_text,
                    candidate_count=len(results),
                    routing_reason="Tier 0 Fast-Path Spec Comparison (多车型极速横向对比)",
                    metadata={"matched_models": models, "matched_field": spec_attr[0] if spec_attr else ""},
                )
                self.cache.put(cache_key, final_res)
                return final_res

        # ── Case B: Single model fast-path lookup ─────────────────────────────
        car_model = models[0] if models else self.fast_index.match_vehicle_model(query)
        if not car_model and car_model_hint:
            car_model = self.fast_index.match_vehicle_model(car_model_hint) or car_model_hint

        # Check Knowledge Graph proprietary technology direct match
        matched_terms = self.fast_index.kg.extract_terms(query)
        if not car_model and matched_terms:
            first_term = matched_terms[0].entity
            rep_cars = first_term.representative_vehicles
            car_model = rep_cars[0] if rep_cars else ""
            if not car_model and "xiaomi" in first_term.brand_key:
                car_model = "小米-SU7 Max"

        if not car_model:
            return None

        # Resolve model to canonical DB record
        if car_model not in self.fast_index.db_records:
            canonical = self.fast_index.match_vehicle_model(car_model)
            if canonical:
                car_model = canonical

        rec = self.fast_index.db_records.get(car_model)
        if not rec:
            return None

        lookup_res = None
        field_name = ""
        if spec_attr:
            field_name = spec_attr[0]
            lookup_res = self.fast_index.lookup_exact_spec(car_model, field_name)

        # Build grounded vehicle snippet & facts summary
        brand = rec.get("brand", "")
        price = rec.get("prize", "")
        category = rec.get("vehicle_category_bottom", "")
        powertrain = rec.get("powertrain_type", "")
        acc = rec.get("acceleration_0_100", "")
        speed = rec.get("max_speed", "")
        rng = rec.get("electric_range", "")
        battery = rec.get("battery_capacity", "")
        hp = rec.get("horsepower", "")

        facts_parts = [f"【{car_model} 官方技术参数】"]
        if price:
            facts_parts.append(f"官方指导价: {price}")
        if acc:
            facts_parts.append(f"0-100km/h加速: {acc}")
        if speed:
            facts_parts.append(f"最高车速: {speed}")
        if rng:
            facts_parts.append(f"纯电续航: {rng}")
        if battery:
            facts_parts.append(f"电池容量: {battery}")
        if hp:
            facts_parts.append(f"最大功率: {hp}")

        # Add specific asked attribute prominence
        if lookup_res:
            lbl, val, _ = lookup_res
            facts_parts.append(f"👉 重点核验项【{lbl}】: {val}")

        # Check for relevant proprietary technology
        if matched_terms:
            t_ent = matched_terms[0].entity
            facts_parts.append(f"搭载科技: {t_ent.name} ({t_ent.summary})")

        facts_text = " | ".join(facts_parts)

        from src.rag_service.schemas import VehicleSearchResult

        result_item = VehicleSearchResult(
            car_model=car_model,
            score=1.0,
            brand=brand,
            price=price,
            category=category,
            powertrain_type=powertrain,
            metadata=rec,
            text_snippet=facts_text,
        )

        latency_ms = (time.perf_counter() - start) * 1000.0
        final_res = TieredSearchResult(
            tier=0,
            is_fast_path=True,
            latency_ms=round(latency_ms, 3),
            results=[result_item],
            facts_summary=facts_text,
            candidate_count=1,
            routing_reason="Tier 0 Fast-Path Exact Spec Match (极速规格/实体直查)",
            metadata={"matched_model": car_model, "matched_field": field_name},
        )

        # Store in cache
        self.cache.put(query, final_res)
        return final_res

    def search_tier1(
        self,
        request: Any,
        top_k: int = 5,
    ) -> TieredSearchResult:
        """
        Execute Tier 1 Agile Single-Shot Hybrid Retrieval (BM25 + Dense).
        Bypasses heavy multi-angle HyDE transformation for fast turnaround.
        """
        start = time.perf_counter()
        query_text = request.query_text or "推荐高品质车型"

        if self.hybrid_pipeline is not None:
            # Run hybrid search with LLM fallback disabled for agile speed
            pipe_res = self.hybrid_pipeline.search(
                query_text, top_k=top_k, use_llm_fallback=False
            )
            from src.rag_service.schemas import VehicleSearchResult
            from src.retrieval.adapters import hybrid_result_to_cars

            cars = hybrid_result_to_cars(pipe_res, limit=top_k)
            search_results = []
            for c in cars:
                meta = c.get("metadata", {})
                search_results.append(
                    VehicleSearchResult(
                        car_model=c.get("car_model", ""),
                        score=float(c.get("score", 0.0)),
                        brand=meta.get("brand", ""),
                        price=meta.get("price", ""),
                        category=meta.get("category", ""),
                        powertrain_type=meta.get("powertrain_type", ""),
                        metadata=meta,
                        text_snippet=c.get("text_snippet", ""),
                    )
                )
            candidate_count = pipe_res.candidate_count
        else:
            search_results = []
            candidate_count = 0

        latency_ms = (time.perf_counter() - start) * 1000.0
        return TieredSearchResult(
            tier=1,
            is_fast_path=False,
            latency_ms=round(latency_ms, 3),
            results=search_results,
            candidate_count=candidate_count,
            routing_reason="Tier 1 Agile Hybrid Retrieval (单路敏捷混合召回)",
        )

    def search_tier2(
        self,
        request: Any,
        top_k: int = 5,
    ) -> TieredSearchResult:
        """
        Execute Tier 2 Deep Multi-Angle Retrieval (Parent-Child & Cross-Document Fusion).
        Used when complex comparative reasoning or technical whitepapers are requested.
        """
        start = time.perf_counter()
        query_text = request.query_text or ""

        # First obtain vehicle candidates
        tier1_res = self.search_tier1(request, top_k=top_k)
        results = tier1_res.results

        # If parent-child retriever is available, enrich candidates with parent document context
        doc_evidence = []
        if self.parent_child_retriever is not None and query_text:
            try:
                doc_res = self.parent_child_retriever.search(
                    query=query_text, top_k_children=6, top_k_parents=3
                )
                if hasattr(doc_res, "results"):
                    for p in doc_res.results:
                        doc_evidence.append(p.content[:300])
            except Exception as e:
                logger.warning(f"Tier 2 Parent-Child enrichment failed: {e}")

        # Enrich vehicle snippets with deep document evidence
        if doc_evidence and results:
            evidence_str = "\n".join(doc_evidence[:2])
            for r in results:
                r.text_snippet = (
                    f"{r.text_snippet}\n【深度文档与横评参考】: {evidence_str[:250]}"
                )

        latency_ms = (time.perf_counter() - start) * 1000.0
        return TieredSearchResult(
            tier=2,
            is_fast_path=False,
            latency_ms=round(latency_ms, 3),
            results=results,
            candidate_count=tier1_res.candidate_count,
            routing_reason="Tier 2 Deep Comparative / Parent-Child Retrieval (深度多视角文档检索)",
            metadata={"doc_evidence_count": len(doc_evidence)},
        )

    def search(
        self,
        request: Any,
        force_tier: Optional[int] = None,
    ) -> TieredSearchResult:
        """
        Intelligent tiered retrieval router.
        Determines query complexity and dispatches to the most cost-effective tier.
        """
        query_text = request.query_text or ""

        if force_tier == 0:
            t0 = self.search_tier0(query_text)
            if t0 is not None and t0.results:
                return t0

        if force_tier == 2:
            return self.search_tier2(request, top_k=request.top_k)

        if force_tier == 1:
            return self.search_tier1(request, top_k=request.top_k)

        # Automatic intelligent tiered routing:
        # 1. Tier 0 Fast-Path Check (exact spec lookup or fast tabular multi-model spec comparison)
        if self.is_tier0_candidate(query_text):
            t0 = self.search_tier0(query_text)
            if t0 is not None and t0.results:
                return t0

        # 2. Tier 2 Deep Multi-Angle / Comparative Retrieval Check
        if self.is_tier2_candidate(query_text):
            return self.search_tier2(request, top_k=request.top_k)

        # 3. Default to Tier 1 Agile Hybrid Retrieval
        return self.search_tier1(request, top_k=request.top_k)
