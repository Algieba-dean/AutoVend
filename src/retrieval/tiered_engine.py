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

import numpy as np

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
    (re.compile(r"官方指导价|指导价|售价|价格|多少钱|多少万|落地价|预算"), "price", "官方指导价"),
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


class TrieNode:
    __slots__ = ("children", "canonical", "is_end")

    def __init__(self):
        self.children: Dict[str, "TrieNode"] = {}
        self.canonical: Optional[str] = None
        self.is_end: bool = False


class EntityIndex:
    """Trie-based entity extraction automaton for O(L) multi-keyword matching."""

    def __init__(self):
        self.root = TrieNode()

    def add_keyword(self, keyword: str, canonical: str) -> None:
        if not keyword:
            return
        node = self.root
        for ch in keyword.lower():
            if ch not in node.children:
                node.children[ch] = TrieNode()
            node = node.children[ch]
        node.is_end = True
        node.canonical = canonical

    def extract_all(self, text: str) -> List[Tuple[int, int, str]]:
        """Extract non-overlapping entity spans (start, end, canonical) in text order."""
        t_lower = text.lower()
        matches: List[Tuple[int, int, str]] = []
        n = len(t_lower)
        i = 0
        while i < n:
            curr = self.root
            longest_match = None
            longest_end = -1
            for j in range(i, n):
                ch = t_lower[j]
                if ch not in curr.children:
                    break
                curr = curr.children[ch]
                if curr.is_end:
                    longest_match = curr.canonical
                    longest_end = j + 1
            if longest_match is not None:
                matches.append((i, longest_end, longest_match))
                i = longest_end
            else:
                i += 1
        return matches


class SemanticQueryCache:
    """
    Production-grade Semantic Query Cache.
    Combines sub-millisecond exact normalized key hits (< 0.05ms) with
    high-threshold (>= 0.96) cosine similarity vector caching.
    """

    def __init__(
        self,
        capacity: int = 1000,
        similarity_threshold: float = 0.96,
        embedding_model: Optional[Any] = None,
    ):
        self.capacity = capacity
        self.similarity_threshold = similarity_threshold
        self.embedding_model = embedding_model
        self._exact_cache: OrderedDict[str, Any] = OrderedDict()
        self._query_embeddings: Dict[str, np.ndarray] = {}
        self._lock = threading.RLock()

    def _normalize_key(self, query: str) -> str:
        q = query.lower().strip()
        q = re.sub(r"[\s\?\!\,\.\;\:\'\"\(\)\-\_，。？！]+", "", q)
        return q

    def _get_embedding(self, query: str) -> Optional[np.ndarray]:
        if not self.embedding_model:
            return None
        try:
            if hasattr(self.embedding_model, "_get_text_embedding"):
                vec = self.embedding_model._get_text_embedding(query)
            elif hasattr(self.embedding_model, "encode"):
                vec = self.embedding_model.encode(query)
            else:
                return None
            arr = np.asarray(vec, dtype=np.float32)
            norm = float(np.linalg.norm(arr))
            return (arr / norm) if norm > 0 else None
        except Exception:
            return None

    def get(self, query: str) -> Optional[Any]:
        norm_key = self._normalize_key(query)
        if not norm_key:
            return None

        with self._lock:
            # 1. Exact normalized hit (< 0.05ms)
            if norm_key in self._exact_cache:
                self._exact_cache.move_to_end(norm_key)
                return self._exact_cache[norm_key]

            # 2. Semantic vector cosine similarity hit (>= 0.96 threshold)
            if self._query_embeddings:
                q_vec = self._get_embedding(query)
                if q_vec is not None:
                    best_sim = -1.0
                    best_key = None
                    for cached_key, c_vec in self._query_embeddings.items():
                        sim = float(np.dot(q_vec, c_vec))
                        if sim > best_sim:
                            best_sim = sim
                            best_key = cached_key
                    if best_sim >= self.similarity_threshold and best_key in self._exact_cache:
                        # 工业级实体一致性校验，确认无跨车型语义漂移
                        def _extract_query_entities(txt: str) -> set:
                            try:
                                idx = FastSpecIndex._instance
                                if idx is not None:
                                    return set(idx.match_all_vehicle_models(txt))
                            except Exception:
                                pass
                            return set(
                                re.findall(
                                    r"(?:model\s*[3ysx]|su7|001|007|l[789]|m[79]|es6|et5|u8|q5|x3)",
                                    txt.lower(),
                                )
                            )

                        q_entities = _extract_query_entities(query)
                        k_entities = _extract_query_entities(best_key)
                        if q_entities == k_entities:
                            self._exact_cache.move_to_end(best_key)
                            return self._exact_cache[best_key]

            return None

    def put(self, query: str, value: Any) -> None:
        norm_key = self._normalize_key(query)
        if not norm_key:
            return

        with self._lock:
            if norm_key in self._exact_cache:
                self._exact_cache.move_to_end(norm_key)
            self._exact_cache[norm_key] = value

            # Cache normalized embedding if available
            q_vec = self._get_embedding(query)
            if q_vec is not None:
                self._query_embeddings[norm_key] = q_vec

            if len(self._exact_cache) > self.capacity:
                oldest_key, _ = self._exact_cache.popitem(last=False)
                self._query_embeddings.pop(oldest_key, None)

    def clear(self) -> None:
        with self._lock:
            self._exact_cache.clear()
            self._query_embeddings.clear()


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


class FastSpecIndex:
    """
    In-memory indexed vehicle specifications and OEM technology facts dynamically derived
    from SQLite VehicleDB. Enables sub-millisecond grounded spec lookup without static dicts.
    """

    _instance: Optional["FastSpecIndex"] = None

    def __init__(self, db: Optional[VehicleDB] = None):
        self.db = db or VehicleDB()
        self.db_records: Dict[str, Dict[str, Any]] = {}
        self.normalized_models: Dict[str, str] = {}  # alias -> canonical car_model
        self.known_brands: Set[str] = set()
        self.kg = AutomotiveKnowledgeGraph.get_instance()
        self.entity_index = EntityIndex()
        self._build_index()

    @classmethod
    def get_instance(cls, db: Optional[VehicleDB] = None) -> "FastSpecIndex":
        if cls._instance is None:
            cls._instance = cls(db=db)
        return cls._instance

    def _build_index(self) -> None:
        """Load vehicle rows into memory from VehicleDB and dynamically build Trie entity index."""
        self.db_records.clear()
        self.normalized_models.clear()
        self.known_brands.clear()
        self.entity_index = EntityIndex()

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

            # Load aliases dynamically from VehicleDB
            aliases = self.db.get_aliases_for_model(model)
            for a in aliases:
                self.normalized_models[a.lower()] = model
                self.normalized_models[a.lower().replace(" ", "")] = model
                self.entity_index.add_keyword(a, model)

        # Standard clean model name variations
        for model in list(self.db_records.keys()):
            clean_model = model.lower().strip()
            self.normalized_models[clean_model] = model
            self.normalized_models[clean_model.replace(" ", "")] = model
            self.normalized_models[clean_model.replace("-", " ")] = model
            self.normalized_models[clean_model.replace("-", "")] = model
            self.entity_index.add_keyword(clean_model, model)
            self.entity_index.add_keyword(clean_model.replace(" ", ""), model)
            self.entity_index.add_keyword(clean_model.replace("-", " "), model)
            self.entity_index.add_keyword(clean_model.replace("-", ""), model)

            if "-" in model:
                parts = model.split("-", 1)
                sub_name = parts[1].lower().strip()
                self.normalized_models[sub_name] = model
                self.normalized_models[sub_name.replace(" ", "")] = model
                self.entity_index.add_keyword(sub_name, model)
                self.entity_index.add_keyword(sub_name.replace(" ", ""), model)

    def match_all_vehicle_models(self, query: str) -> List[str]:
        """Find all distinct canonical car models mentioned in user query text via Trie automaton."""
        matches = self.entity_index.extract_all(query)
        result: List[str] = []
        for _, _, canonical in matches:
            if canonical in self.db_records and canonical not in result:
                result.append(canonical)

        # Fallback to normalized_models map if Trie missed any edge case
        if not result:
            q_lower = query.lower()
            matched_spans: List[Tuple[int, int, str]] = []
            for key in sorted(self.normalized_models.keys(), key=len, reverse=True):
                if len(key) < 2:
                    continue
                pos = q_lower.find(key)
                if pos != -1:
                    end = pos + len(key)
                    if any(not (end <= s or pos >= e) for s, e, _ in matched_spans):
                        continue
                    matched_spans.append((pos, end, self.normalized_models[key]))
            matched_spans.sort(key=lambda x: x[0])
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

        # Check direct vehicle DB attributes with synonym field mapping
        field_synonyms = {
            "acceleration_0_100": [
                "acceleration_0_100",
                "zero_to_one_hundred_km_h_acceleration_time",
            ],
            "max_speed": ["max_speed", "top_speed"],
            "electric_range": ["electric_range", "driving_range"],
            "price": ["price"],
            "horsepower": ["horsepower"],
            "torque": ["torque"],
            "battery_capacity": ["battery_capacity"],
            "wheelbase": ["wheelbase"],
            "seat_layout": ["seat_layout"],
            "drive_type": ["drive_type"],
            "powertrain_type": ["powertrain_type"],
            "autonomous_driving_level": ["autonomous_driving_level"],
            "charging_tech": ["charging_tech"],
            "motor_tech": ["motor_tech"],
        }
        candidates = field_synonyms.get(field_name, [field_name])
        for cand in candidates:
            if cand in rec and rec[cand]:
                val = rec[cand]
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
                price = rec.get("price", "")
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
        price = rec.get("price", "")
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

        # Entity-scoped Parent-Child Retrieval (杜绝跨实体张冠李戴投毒)
        candidate_models = [r.car_model for r in results]
        scoped_contexts: Dict[str, List[Any]] = {}
        total_doc_count = 0
        if self.parent_child_retriever is not None and query_text and candidate_models:
            from src.retrieval.parent_child_retriever import (
                format_isolated_llm_context,
                retrieve_multi_vehicle_context,
            )

            scoped_contexts = retrieve_multi_vehicle_context(
                query=query_text,
                car_models=candidate_models,
                parent_child_retriever=self.parent_child_retriever,
                top_k_per_vehicle=2,
            )

        # Enrich vehicle snippets ONLY with entity-specific evidence
        for r in results:
            chunks = scoped_contexts.get(r.car_model, [])
            if chunks:
                total_doc_count += len(chunks)
                evidence_str = "\n".join([f"  - {getattr(c, 'content', str(c)).strip()[:200]}" for c in chunks[:2]])
                r.text_snippet = (
                    f"{r.text_snippet}\n【{r.car_model} 专属深度测评参考】:\n{evidence_str[:250]}"
                )

        isolated_context = ""
        if scoped_contexts:
            try:
                from src.retrieval.parent_child_retriever import format_isolated_llm_context

                isolated_context = format_isolated_llm_context(scoped_contexts)
            except Exception:
                pass

        latency_ms = (time.perf_counter() - start) * 1000.0
        return TieredSearchResult(
            tier=2,
            is_fast_path=False,
            latency_ms=round(latency_ms, 3),
            results=results,
            candidate_count=tier1_res.candidate_count,
            metadata={
                "doc_evidence_count": total_doc_count,
                "scoped_entities": list(scoped_contexts.keys()),
                "isolated_context": isolated_context,
            },
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
