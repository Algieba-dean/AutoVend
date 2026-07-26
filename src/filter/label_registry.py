"""
标签注册表

从 LabelsTree.json 加载标签定义，分类管理所有标签类型：
- 树形标签 (tree): vehicle_category, brand
- 范围标签 (range): prize, horsepower, wheelbase 等有序候选值
- 枚举标签 (enum): powertrain_type, design_style, drive_type 等
- 布尔标签 (boolean): abs, esp, ota_updates 等 Yes/No
- 等级标签 (grade): noise_insulation, off_road_capability 等有序等级
- 模糊标签 (ambiguous): size, comfort_level 等 AmbiguousLabels
"""

import json
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from src.utils.logger import get_logger


class LabelType(str, Enum):
    """标签类型枚举"""

    TREE = "tree"
    RANGE = "range"
    ENUM = "enum"
    BOOLEAN = "boolean"
    GRADE = "grade"
    AMBIGUOUS = "ambiguous"


class LabelInfo:
    """单个标签的元信息"""

    def __init__(
        self,
        name: str,
        label_type: LabelType,
        candidates: List[str],
        aliases: Optional[List[str]] = None,
        is_precise: bool = True,
    ):
        self.name = name
        self.label_type = label_type
        self.candidates = candidates
        self.aliases = aliases or []
        self.is_precise = is_precise

        # 候选值 → index 映射（用于范围比较）
        self.value_index: Dict[str, int] = {v: i for i, v in enumerate(candidates)}

        # 别名 → 实际值映射
        self.alias_to_value: Dict[str, str] = {}
        if aliases and len(aliases) <= len(candidates):
            for alias, value in zip(aliases, candidates):
                self.alias_to_value[alias] = value

    def resolve_alias(self, value: str) -> str:
        """将别名转换为实际值，如果不是别名则原样返回"""
        return self.alias_to_value.get(value.lower(), value)

    def get_index(self, value: str) -> Optional[int]:
        """获取候选值的有序索引"""
        return self.value_index.get(value.lower())

    def get_values_in_range(
        self, min_index: Optional[int] = None, max_index: Optional[int] = None
    ) -> List[str]:
        """获取指定索引范围内的所有候选值"""
        lo = min_index if min_index is not None else 0
        hi = max_index if max_index is not None else len(self.candidates) - 1
        return [v for i, v in enumerate(self.candidates) if lo <= i <= hi and v.lower() != "none"]

    def get_values_gte(self, value: str) -> List[str]:
        """获取 >= 某值的所有候选值"""
        idx = self.get_index(value.lower())
        if idx is None:
            return []
        return self.get_values_in_range(min_index=idx)

    def get_values_lte(self, value: str) -> List[str]:
        """获取 <= 某值的所有候选值"""
        idx = self.get_index(value.lower())
        if idx is None:
            return []
        return self.get_values_in_range(max_index=idx)


class LabelRegistry:
    """
    标签注册表

    管理所有标签的元信息，提供标签分类查询、别名解析、
    树形展开、范围匹配等核心功能。
    """

    # 布尔标签列表
    BOOLEAN_LABELS: Set[str] = {
        "abs",
        "esp",
        "voice_interaction",
        "ota_updates",
        "adaptive_cruise_control",
        "traffic_jam_assist",
        "automatic_emergency_braking",
        "lane_keep_assist",
        "remote_parking",
        "auto_parking",
        "blind_spot_detection",
        "fatigue_driving_detection",
        "city_commuting",
        "highway_long_distance",
        "cargo_capability",
    }

    # 等级标签列表（有序 Low/Medium/High 或数值型）
    GRADE_LABELS: Set[str] = {
        "noise_insulation",
        "body_line_smoothness",
        "passability",
        "off_road_capability",
        "cold_resistance",
        "heat_resistance",
        "airbag_count",
    }

    # 有别名的范围标签（name → alias_name）
    RANGE_ALIAS_MAP: Dict[str, str] = {
        "prize": "prize_alias",
        "passenger_space_volume": "passenger_space_volume_alias",
        "trunk_volume": "trunk_volume_alias",
        "wheelbase": "wheelbase_alias",
        "chassis_height": "chassis_height_alias",
        "motor_power": "motor_power_alias",
        "battery_capacity": "battery_capacity_alias",
        "fuel_tank_capacity": "fuel_tank_capacity_alias",
        "horsepower": "horsepower_alias",
        "torque": "torque_alias",
        "zero_to_one_hundred_km_h_acceleration_time": "zero_to_one_hundred_km_h_acceleration_time_alias",
        "top_speed": "top_speed_alias",
        "fuel_consumption": "fuel_consumption_alias",
        "electric_consumption": "electric_consumption_alias",
        "driving_range": "driving_range_alias",
    }

    def __init__(self, labels_tree_path: Optional[str] = None):
        self.logger = get_logger(f"{self.__class__.__module__}.{self.__class__.__name__}")

        # 标签存储
        self.labels: Dict[str, LabelInfo] = {}

        # 树形结构原始数据
        self.vehicle_category_tree: Dict[str, Any] = {}
        self.brand_tree: Dict[str, Any] = {}

        # 树形结构的展开缓存: 任意节点名 → 叶子节点列表
        self._tree_expand_cache: Dict[str, List[str]] = {}

        # 加载标签定义
        if labels_tree_path is None:
            labels_tree_path = str(
                Path(__file__).parent.parent.parent
                / "DataInUse"
                / "VehicleData"
                / "LabelsTree.json"
            )
        self._load(labels_tree_path)

    def _load(self, path: str) -> None:
        """从 LabelsTree.json 加载并分类所有标签"""
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        precise = data.get("precise_needs", {})
        ambiguous = data.get("ambiguous_needs", {})

        # 1. 树形标签
        self.vehicle_category_tree = precise.get("vehicle_category", {})
        self.brand_tree = precise.get("brand", {})
        self._build_tree_cache()

        # 2. 处理 precise_needs 中的非树形标签
        skip_keys = {"vehicle_category", "brand"}
        alias_keys = {v for v in self.RANGE_ALIAS_MAP.values()}

        for key, value in precise.items():
            if key in skip_keys or key in alias_keys:
                continue
            if not isinstance(value, list):
                continue

            candidates = [v.lower() for v in value]

            if key in self.BOOLEAN_LABELS:
                self.labels[key] = LabelInfo(
                    name=key,
                    label_type=LabelType.BOOLEAN,
                    candidates=candidates,
                    is_precise=True,
                )
            elif key in self.GRADE_LABELS:
                self.labels[key] = LabelInfo(
                    name=key,
                    label_type=LabelType.GRADE,
                    candidates=candidates,
                    is_precise=True,
                )
            elif key in self.RANGE_ALIAS_MAP:
                alias_key = self.RANGE_ALIAS_MAP[key]
                alias_list = precise.get(alias_key, [])
                aliases = [a.lower() for a in alias_list] if alias_list else []
                self.labels[key] = LabelInfo(
                    name=key,
                    label_type=LabelType.RANGE,
                    candidates=candidates,
                    aliases=aliases,
                    is_precise=True,
                )
            else:
                self.labels[key] = LabelInfo(
                    name=key,
                    label_type=LabelType.ENUM,
                    candidates=candidates,
                    is_precise=True,
                )

        # 3. 模糊标签
        for key, value in ambiguous.items():
            if isinstance(value, list):
                candidates = [v.lower() for v in value]
                self.labels[key] = LabelInfo(
                    name=key,
                    label_type=LabelType.AMBIGUOUS,
                    candidates=candidates,
                    is_precise=False,
                )

        self.logger.info(
            f"标签注册表加载完成: {len(self.labels)} 个标签, 树形: vehicle_category + brand"
        )

    # ------------------------------------------------------------------
    # 树形展开
    # ------------------------------------------------------------------

    def _build_tree_cache(self) -> None:
        """构建树形结构的展开缓存"""
        self._tree_expand_cache.clear()

        # vehicle_category 树
        self._expand_tree_node(self.vehicle_category_tree, "vehicle_category")

        # brand 树
        self._expand_tree_node(self.brand_tree, "brand")

    def _expand_tree_node(self, node: Any, prefix: str) -> List[str]:
        """递归展开树节点，返回所有叶子节点"""
        if isinstance(node, list):
            leaves = [v.lower() for v in node]
            return leaves
        elif isinstance(node, dict):
            all_leaves: List[str] = []
            for key, child in node.items():
                child_leaves = self._expand_tree_node(child, prefix)
                self._tree_expand_cache[key.lower()] = child_leaves
                all_leaves.extend(child_leaves)
            return all_leaves
        else:
            return [str(node).lower()]

    def expand_tree(self, value: str) -> List[str]:
        """
        展开树形标签值到叶子节点列表

        Args:
            value: 任意层级的树形标签值（如 "suv", "crossover suv", "compact suv"）

        Returns:
            叶子节点列表。如果 value 本身就是叶子，返回 [value]。
        """
        lower_val = value.lower()
        if lower_val in self._tree_expand_cache:
            return self._tree_expand_cache[lower_val]
        # 可能本身就是叶子节点
        return [lower_val]

    def is_tree_value(self, value: str) -> bool:
        """检查值是否在任何树形结构中"""
        lower_val = value.lower()
        if lower_val in self._tree_expand_cache:
            return True
        # 检查是否是叶子节点
        for leaves in self._tree_expand_cache.values():
            if lower_val in leaves:
                return True
        return False

    def get_tree_field(self, value: str) -> Optional[str]:
        """
        判断一个树形值属于哪个字段（vehicle_category 还是 brand）

        Returns:
            "vehicle_category_bottom" 或 "brand"，无法识别则 None
        """
        lower_val = value.lower()
        # 检查 vehicle_category
        vc_leaves = set()
        for key, child in self.vehicle_category_tree.items():
            expanded = self.expand_tree(key)
            vc_leaves.update(expanded)

        if lower_val in self._tree_expand_cache:
            expanded = self._tree_expand_cache[lower_val]
            if expanded and expanded[0] in vc_leaves:
                return "vehicle_category_bottom"
            else:
                return "brand"

        if lower_val in vc_leaves:
            return "vehicle_category_bottom"

        # 检查 brand
        brand_leaves = set()
        for key, child in self.brand_tree.items():
            expanded = self.expand_tree(key)
            brand_leaves.update(expanded)

        if lower_val in brand_leaves:
            return "brand"

        return None

    # ------------------------------------------------------------------
    # 标签查询接口
    # ------------------------------------------------------------------

    def get_label(self, name: str) -> Optional[LabelInfo]:
        """获取标签信息"""
        return self.labels.get(name.lower())

    def get_label_type(self, name: str) -> Optional[LabelType]:
        """获取标签类型"""
        label = self.labels.get(name.lower())
        return label.label_type if label else None

    def resolve_alias(self, label_name: str, value: str) -> str:
        """解析别名为实际值"""
        label = self.labels.get(label_name.lower())
        if label:
            return label.resolve_alias(value)
        return value

    def get_all_labels_by_type(self, label_type: LabelType) -> List[LabelInfo]:
        """获取指定类型的所有标签"""
        return [info for info in self.labels.values() if info.label_type == label_type]

    def get_precise_labels(self) -> List[str]:
        """获取所有精确标签名"""
        return [name for name, info in self.labels.items() if info.is_precise]

    def get_ambiguous_labels(self) -> List[str]:
        """获取所有模糊标签名"""
        return [name for name, info in self.labels.items() if not info.is_precise]

    def get_all_db_columns(self) -> List[str]:
        """获取所有应存入SQLite的字段名（不含 car_model）"""
        columns = ["vehicle_category_bottom", "brand"]
        for name in self.labels:
            if name not in columns:
                columns.append(name)
        return columns

    # ------------------------------------------------------------------
    # 统计与调试
    # ------------------------------------------------------------------

    def summary(self) -> Dict[str, Any]:
        """返回注册表摘要"""
        type_counts: Dict[str, int] = {}
        for info in self.labels.values():
            t = info.label_type.value
            type_counts[t] = type_counts.get(t, 0) + 1

        return {
            "total_labels": len(self.labels),
            "type_counts": type_counts,
            "tree_nodes": len(self._tree_expand_cache),
            "range_labels_with_alias": [
                name
                for name, info in self.labels.items()
                if info.label_type == LabelType.RANGE and info.aliases
            ],
        }
