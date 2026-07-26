"""
混合检索管道

Pipeline: 用户查询 → 意图解析 → SQLite粗筛 → RAG语义精排 → 结果输出

1. 规则引擎解析 + LLM fallback
2. FilterEngine 执行结构化过滤获取候选 car_model 列表
3. 将候选列表传入 VehicleRetriever，限制 ChromaDB 搜索范围
4. 返回精排后的 SearchResponse
"""

import time
from typing import Any, Dict, List, Optional

from src.filter.filter_engine import FilterEngine, FilterResult
from src.filter.label_registry import LabelRegistry
from src.filter.llm_parser import LLMParser
from src.filter.query_parser import ParsedQuery, QueryParser
from src.filter.vehicle_db import VehicleDB
from src.models.query import Query, SearchResponse
from src.utils.logger import get_logger


class HybridPipelineResult:
    """混合管道结果元数据"""

    def __init__(self):
        self.parse_method: str = ""
        self.parsed_conditions: Dict[str, Any] = {}
        self.matched_keywords: List[str] = []
        self.filter_result: Optional[FilterResult] = None
        self.degrade_level: int = -1
        self.candidate_count: int = 0
        self.rag_result_count: int = 0
        self.total_time: float = 0.0
        self.search_response: Optional[SearchResponse] = None

    def summary(self) -> Dict[str, Any]:
        return {
            "parse_method": self.parse_method,
            "parsed_conditions": self.parsed_conditions,
            "matched_keywords": self.matched_keywords,
            "degrade_level": self.degrade_level,
            "candidate_count": self.candidate_count,
            "rag_result_count": self.rag_result_count,
            "total_time": round(self.total_time, 3),
        }


class HybridPipeline:
    """
    混合检索管道

    整合意图解析、SQLite粗筛、RAG精排三个阶段。
    """

    # 如果规则引擎匹配到的关键词数少于此值，尝试 LLM 补充
    LLM_FALLBACK_THRESHOLD = 1

    def __init__(
        self,
        registry: Optional[LabelRegistry] = None,
        db: Optional[VehicleDB] = None,
        filter_engine: Optional[FilterEngine] = None,
        query_parser: Optional[QueryParser] = None,
        llm_parser: Optional[LLMParser] = None,
        retriever: Optional[Any] = None,
    ):
        self.logger = get_logger(f"{self.__class__.__module__}.{self.__class__.__name__}")

        # 共享 registry
        self.registry = registry or LabelRegistry()
        self.db = db or VehicleDB(registry=self.registry)
        self.filter_engine = filter_engine or FilterEngine(db=self.db, registry=self.registry)
        self.query_parser = query_parser or QueryParser(registry=self.registry)
        self.llm_parser = llm_parser
        self.retriever = retriever

    def ensure_db_loaded(self) -> None:
        """确保 SQLite 数据库已加载"""
        if self.db.count() == 0:
            self.logger.info("SQLite 数据库为空，开始导入...")
            self.db.import_from_toml_dir()

    # ------------------------------------------------------------------
    # 主入口
    # ------------------------------------------------------------------

    def search(
        self,
        query_text: str,
        top_k: int = 10,
        use_llm_fallback: bool = True,
    ) -> HybridPipelineResult:
        """
        执行混合检索

        Args:
            query_text: 用户自然语言查询
            top_k: 返回结果数
            use_llm_fallback: 是否启用 LLM fallback

        Returns:
            HybridPipelineResult 包含完整的管道执行信息
        """
        start = time.time()
        result = HybridPipelineResult()
        self.ensure_db_loaded()

        # ---- Phase 1: 意图解析 ----
        parsed = self._parse_intent(query_text, use_llm_fallback, result)

        # ---- Phase 2: SQLite 粗筛 ----
        filter_result = self._coarse_filter(parsed, result)

        # ---- Phase 3: RAG 精排 ----
        self._semantic_rerank(query_text, filter_result, top_k, result)

        result.total_time = time.time() - start
        self.logger.info(
            f"混合检索完成: {result.candidate_count} 候选 → "
            f"{result.rag_result_count} 精排结果, "
            f"耗时 {result.total_time:.3f}s"
        )
        return result

    # ------------------------------------------------------------------
    # Phase 1: 意图解析
    # ------------------------------------------------------------------

    def _parse_intent(
        self,
        query_text: str,
        use_llm_fallback: bool,
        result: HybridPipelineResult,
    ) -> Dict[str, Any]:
        """解析用户意图"""
        # 1. 规则引擎
        parsed: ParsedQuery = self.query_parser.parse(query_text)
        conditions = parsed.conditions
        result.matched_keywords = parsed.matched_keywords
        result.parse_method = "rule"

        # 2. LLM fallback（规则引擎结果不充分时）
        if (
            use_llm_fallback
            and len(parsed.matched_keywords) < self.LLM_FALLBACK_THRESHOLD
            and self.llm_parser is not None
            and self.llm_parser.is_available()
        ):
            self.logger.info("规则引擎结果不充分，尝试 LLM 解析")
            llm_conditions = self.llm_parser.parse(query_text)
            if llm_conditions:
                # 合并：LLM 补充规则引擎未覆盖的条件
                for k, v in llm_conditions.items():
                    if k not in conditions:
                        conditions[k] = v
                result.parse_method = "rule+llm"

        result.parsed_conditions = conditions
        return conditions

    # ------------------------------------------------------------------
    # Phase 2: SQLite 粗筛
    # ------------------------------------------------------------------

    def _coarse_filter(
        self,
        conditions: Dict[str, Any],
        result: HybridPipelineResult,
    ) -> FilterResult:
        """执行 SQLite 粗筛"""
        filter_result = self.filter_engine.filter(conditions)
        result.filter_result = filter_result
        result.degrade_level = filter_result.degrade_level
        result.candidate_count = filter_result.total_candidates
        return filter_result

    # ------------------------------------------------------------------
    # Phase 3: RAG 精排
    # ------------------------------------------------------------------

    def _semantic_rerank(
        self,
        query_text: str,
        filter_result: FilterResult,
        top_k: int,
        result: HybridPipelineResult,
    ) -> None:
        """用 RAG 对粗筛候选进行语义精排"""
        if self.retriever is None:
            self.logger.warning("未配置 retriever，跳过 RAG 精排")
            result.rag_result_count = 0
            return

        # 构建 Query 对象
        query = Query(text=query_text, top_k=top_k)

        # 如果有候选列表，注入到 query.filters 中
        if filter_result.car_models:
            # 使用 car_model_candidates 传递候选列表
            query.filters = query.filters or {}
            query.filters["car_model_candidates"] = filter_result.car_models

        try:
            response = self.retriever.search(query)
            result.search_response = response
            result.rag_result_count = response.total_count
        except Exception as e:
            self.logger.error(f"RAG 精排失败: {e}")
            result.rag_result_count = 0

    # ------------------------------------------------------------------
    # 便捷接口
    # ------------------------------------------------------------------

    def filter_only(self, query_text: str) -> FilterResult:
        """仅执行粗筛（不走 RAG）"""
        self.ensure_db_loaded()
        parsed = self.query_parser.parse(query_text)
        return self.filter_engine.filter(parsed.conditions)

    def get_candidates(self, query_text: str) -> List[str]:
        """获取粗筛候选 car_model 列表"""
        result = self.filter_only(query_text)
        return result.car_models

    def close(self) -> None:
        """释放资源"""
        self.db.close()
