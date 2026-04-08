"""
过滤引擎

接收结构化查询 dict，根据标签类型自动分派匹配策略，
生成 SQL WHERE 子句并执行查询。支持降级策略保证有结果返回。
"""

from typing import Any, Dict, List, Optional, Tuple

from src.filter.label_registry import LabelInfo, LabelRegistry, LabelType
from src.filter.vehicle_db import VehicleDB
from src.utils.logger import get_logger


class FilterResult:
    """过滤结果"""

    def __init__(
        self,
        car_models: List[str],
        applied_query: Dict[str, Any],
        degrade_level: int,
        total_candidates: int,
    ):
        self.car_models = car_models
        self.applied_query = applied_query
        self.degrade_level = degrade_level
        self.total_candidates = total_candidates

    def __repr__(self) -> str:
        return (
            f"FilterResult(candidates={self.total_candidates}, "
            f"degrade_level={self.degrade_level})"
        )


class FilterEngine:
    """
    过滤引擎

    根据标签类型自动选择匹配策略：
    - 树形标签: 展开到叶子节点，用 IN 查询
    - 范围标签: 支持精确 / ≥ / ≤ / 区间匹配
    - 枚举标签: 精确匹配
    - 布尔标签: Yes/No 匹配
    - 等级标签: 有序比较
    - 模糊标签: 精确匹配（降级时优先去除）

    支持降级策略：
    Level 0: 全部条件
    Level 1: 去除模糊标签
    Level 2: 去除等级标签，保留核心
    Level 3: 仅保留品牌或车型
    Level 4: 放弃粗筛，返回空（交给 RAG）
    """

    # 树形层级 key → 对应的 DB 列名
    TREE_LEVEL_KEYS = {
        "vehicle_category_top": "vehicle_category_bottom",
        "vehicle_category_middle": "vehicle_category_bottom",
        "brand_area": "brand",
        "brand_country": "brand",
    }

    # 降级时的核心标签（Level 2 保留）
    CORE_LABELS = {
        "brand",
        "vehicle_category_bottom",
        "prize",
        "powertrain_type",
    }

    def __init__(
        self,
        db: Optional[VehicleDB] = None,
        registry: Optional[LabelRegistry] = None,
        min_candidates: int = 5,
        max_candidates: int = 200,
    ):
        self.logger = get_logger(
            f"{self.__class__.__module__}.{self.__class__.__name__}"
        )
        self.registry = registry or LabelRegistry()
        self.db = db or VehicleDB(registry=self.registry)
        self.min_candidates = min_candidates
        self.max_candidates = max_candidates

    def filter(
        self,
        structured_query: Dict[str, Any],
        enable_degrade: bool = True,
    ) -> FilterResult:
        """
        执行结构化过滤

        Args:
            structured_query: 结构化查询 dict
                key: 标签名或树形层级名
                value: 匹配值，支持以下格式：
                  - str: 精确匹配 / 别名
                  - list: OR 匹配（多值取并集）
                  - dict: 范围匹配 {"op": "gte"/"lte"/"between",
                          "value": ... / "min": ..., "max": ...}
            enable_degrade: 是否启用降级策略

        Returns:
            FilterResult
        """
        if not structured_query:
            return FilterResult([], {}, 4, 0)

        # 尝试各降级级别
        for level in range(5):
            query = self._apply_degrade(structured_query, level)
            if not query:
                continue

            clauses, params = self._build_where(query)
            if not clauses:
                continue

            rows = self.db.query(clauses, params, limit=self.max_candidates)
            car_models = [r["car_model"] for r in rows]

            if car_models and len(car_models) >= self.min_candidates:
                return FilterResult(
                    car_models=car_models,
                    applied_query=query,
                    degrade_level=level,
                    total_candidates=len(car_models),
                )

            if not enable_degrade:
                return FilterResult(
                    car_models=car_models,
                    applied_query=query,
                    degrade_level=level,
                    total_candidates=len(car_models),
                )

            self.logger.debug(
                f"降级 Level {level}: {len(car_models)} 辆候选, "
                f"不足 {self.min_candidates}, 继续降级"
            )

        # 全部降级后仍无结果
        return FilterResult([], structured_query, 4, 0)

    # ------------------------------------------------------------------
    # 降级策略
    # ------------------------------------------------------------------

    def _apply_degrade(self, query: Dict[str, Any], level: int) -> Dict[str, Any]:
        """根据降级级别裁剪查询条件"""
        if level == 0:
            return dict(query)

        if level == 1:
            # 去除模糊标签
            ambiguous = set(self.registry.get_ambiguous_labels())
            return {k: v for k, v in query.items() if k not in ambiguous}

        if level == 2:
            # 仅保留核心标签 + 树形查询
            result = {}
            for k, v in query.items():
                if k in self.CORE_LABELS:
                    result[k] = v
                elif self.registry.is_tree_value(str(v) if isinstance(v, str) else ""):
                    result[k] = v
            return result

        if level == 3:
            # 仅保留品牌或车型
            result = {}
            for k in (
                "brand",
                "vehicle_category_bottom",
                "vehicle_category_top",
                "vehicle_category_middle",
            ):
                if k in query:
                    result[k] = query[k]
            # 检查树形值
            for k, v in query.items():
                if isinstance(v, str) and self.registry.is_tree_value(v):
                    field = self.registry.get_tree_field(v)
                    if field:
                        result[field] = v
            return result if result else {}

        # level >= 4: 放弃
        return {}

    # ------------------------------------------------------------------
    # SQL 构建
    # ------------------------------------------------------------------

    def _build_where(self, query: Dict[str, Any]) -> Tuple[List[str], List[Any]]:
        """将结构化查询转为 SQL WHERE 子句"""
        clauses: List[str] = []
        params: List[Any] = []

        for key, value in query.items():
            c, p = self._build_single_clause(key, value)
            if c:
                clauses.append(c)
                params.extend(p)

        return clauses, params

    def _build_single_clause(self, key: str, value: Any) -> Tuple[str, List[Any]]:
        """为单个条件构建 SQL 子句"""
        key_lower = key.lower()

        # 0. 树形层级 key 映射（如 vehicle_category_top → vehicle_category_bottom）
        db_col = self.TREE_LEVEL_KEYS.get(key_lower)
        if db_col:
            if isinstance(value, str):
                return self._build_tree_clause(db_col, value)
            if isinstance(value, list):
                all_leaves: List[str] = []
                for v in value:
                    all_leaves.extend(self.registry.expand_tree(str(v)))
                if all_leaves:
                    ph = ", ".join("?" for _ in all_leaves)
                    return f'"{db_col}" IN ({ph})', all_leaves
                return "", []

        # 1. 检查是否是树形查询（值是树形节点名）
        if isinstance(value, str) and self.registry.is_tree_value(value):
            field = self.registry.get_tree_field(value)
            if field:
                return self._build_tree_clause(field, value)

        # 2. 检查是否是已知标签
        label = self.registry.get_label(key_lower)

        if label is None:
            # 尝试作为树形值处理
            if isinstance(value, str):
                field = self.registry.get_tree_field(value)
                if field:
                    return self._build_tree_clause(field, value)
            return "", []

        # 3. 根据标签类型分派
        if isinstance(value, dict):
            return self._build_range_op_clause(label, value)
        elif isinstance(value, list):
            return self._build_in_clause(label, value)
        else:
            return self._build_exact_clause(label, str(value))

    def _build_tree_clause(self, field: str, value: str) -> Tuple[str, List[Any]]:
        """树形标签: 展开到叶子节点用 IN"""
        leaves = self.registry.expand_tree(value)
        if not leaves:
            return "", []

        if len(leaves) == 1:
            return f'"{field}" = ?', [leaves[0]]

        placeholders = ", ".join("?" for _ in leaves)
        return f'"{field}" IN ({placeholders})', leaves

    def _build_exact_clause(
        self, label: LabelInfo, value: str
    ) -> Tuple[str, List[Any]]:
        """精确/别名匹配"""
        resolved = label.resolve_alias(value.lower())
        return f'"{label.name}" = ?', [resolved]

    def _build_in_clause(
        self, label: LabelInfo, values: List[str]
    ) -> Tuple[str, List[Any]]:
        """多值 OR 匹配"""
        resolved = [label.resolve_alias(v.lower()) for v in values]
        placeholders = ", ".join("?" for _ in resolved)
        return f'"{label.name}" IN ({placeholders})', resolved

    def _build_range_op_clause(
        self, label: LabelInfo, spec: Dict[str, Any]
    ) -> Tuple[str, List[Any]]:
        """
        范围操作匹配

        spec 格式:
          {"op": "gte", "value": "200-300 hp"}   → 大于等于
          {"op": "lte", "value": "200-300 hp"}   → 小于等于
          {"op": "between", "min": "...", "max": "..."}  → 区间
          {"op": "eq", "value": "..."}           → 精确
        """
        op = spec.get("op", "eq")
        if label.label_type != LabelType.RANGE:
            # 非范围标签，回退到精确匹配
            val = spec.get("value", "")
            return self._build_exact_clause(label, str(val))

        if op == "eq":
            val = label.resolve_alias(str(spec.get("value", "")))
            return f'"{label.name}" = ?', [val]

        if op == "gte":
            val = label.resolve_alias(str(spec.get("value", "")))
            matches = label.get_values_gte(val)
            if not matches:
                return "", []
            placeholders = ", ".join("?" for _ in matches)
            return f'"{label.name}" IN ({placeholders})', matches

        if op == "lte":
            val = label.resolve_alias(str(spec.get("value", "")))
            matches = label.get_values_lte(val)
            if not matches:
                return "", []
            placeholders = ", ".join("?" for _ in matches)
            return f'"{label.name}" IN ({placeholders})', matches

        if op == "between":
            min_val = label.resolve_alias(str(spec.get("min", "")))
            max_val = label.resolve_alias(str(spec.get("max", "")))
            min_idx = label.get_index(min_val)
            max_idx = label.get_index(max_val)
            if min_idx is None or max_idx is None:
                return "", []
            matches = label.get_values_in_range(min_idx, max_idx)
            if not matches:
                return "", []
            placeholders = ", ".join("?" for _ in matches)
            return f'"{label.name}" IN ({placeholders})', matches

        return "", []
