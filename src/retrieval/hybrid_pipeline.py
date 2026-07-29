"""
混合检索管道

Pipeline: 用户查询 → 意图解析 → SQLite粗筛 → 稠密+稀疏双路召回 → RRF融合 → 输出

1. 规则引擎解析 + LLM fallback
2. FilterEngine 执行结构化过滤获取候选 car_model 列表（元数据预过滤）
3. 候选列表同时约束向量检索与 BM25 检索，两路独立召回
4. RRF 融合两路排名，返回 SearchResponse

第 2 步是延迟不随目录规模增长的原因：只有通过结构化过滤的候选才会被打分。
第 3 步覆盖两类互补的失败：向量检索泛化但模糊精确 token，BM25 精确但不泛化。
"""

import time
from typing import Any, Dict, List, Optional

from src.filter.filter_engine import FilterEngine, FilterResult
from src.filter.label_registry import LabelRegistry
from src.filter.llm_parser import LLMParser
from src.filter.query_parser import ParsedQuery, QueryParser
from src.filter.vehicle_db import VehicleDB
from src.models.query import Query, SearchResponse
from src.retrieval.fusion import DEFAULT_K as DEFAULT_RRF_K
from src.retrieval.fusion import reciprocal_rank_fusion, weights_for_query
from src.utils.logger import get_logger

#: 融合时每一路多取的倍数。见 `_semantic_rerank` 中的说明。
FUSION_DEPTH_MULTIPLIER = 4


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
        self.sparse_result_count: int = 0
        self.fusion_weights = None
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
            "sparse_result_count": self.sparse_result_count,
            "fusion_weights": (
                {
                    "dense": self.fusion_weights.dense,
                    "sparse": self.fusion_weights.sparse,
                    "reason": self.fusion_weights.reason,
                }
                if self.fusion_weights
                else None
            ),
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
        sparse_index: Optional[Any] = None,
        fusion_k: int = DEFAULT_RRF_K,
        dynamic_fusion_weights: bool = False,
    ):
        self.logger = get_logger(f"{self.__class__.__module__}.{self.__class__.__name__}")

        # 共享 registry
        self.registry = registry or LabelRegistry()
        self.db = db or VehicleDB(registry=self.registry)
        self.filter_engine = filter_engine or FilterEngine(db=self.db, registry=self.registry)
        self.query_parser = query_parser or QueryParser(registry=self.registry)
        self.llm_parser = llm_parser
        self.retriever = retriever
        self.sparse_index = sparse_index
        self.fusion_k = fusion_k
        self.dynamic_fusion_weights = dynamic_fusion_weights

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
        """对粗筛候选做稠密召回，可选与 BM25 稀疏召回做 RRF 融合"""
        if self.retriever is None:
            self.logger.warning("未配置 retriever，跳过 RAG 精排")
            result.rag_result_count = 0
            return

        # 全套 Query Transformation：重写、拓展、HyDE 伪文档生成、多路展开与子查询拆解
        from src.retrieval.query_transform import QueryTransformationEngine

        transformer = QueryTransformationEngine()
        transform_res = transformer.transform_all(query_text)
        search_query_text = transform_res["expanded_query"]

        # 融合需要更深的稠密候选池
        dense_depth = top_k * FUSION_DEPTH_MULTIPLIER if self.sparse_index else top_k
        query = Query(text=search_query_text, top_k=dense_depth)

        # 如果有候选列表，注入到 query.filters 中（元数据预过滤）
        if filter_result.car_models:
            query.filters = query.filters or {}
            query.filters["car_model_candidates"] = filter_result.car_models

        # 并行执行：稠密召回 (ChromaDB HyDE) 与 稀疏召回 (BM25)
        import concurrent.futures

        dense_response = None
        sparse_hits = []

        def _do_dense():
            # 优先使用 HyDE 假设性文档进行向量召回，获得极高的 Doc-to-Doc 向量余弦相似度
            hyde_query = Query(
                text=transform_res["hyde_document"], top_k=dense_depth, filters=query.filters
            )
            try:
                return self.retriever.search(hyde_query)
            except Exception:
                return self.retriever.search(query)

        def _do_sparse():
            if self.sparse_index is not None:
                # 若存在子查询拆解，分别对比检索并合并
                if len(transform_res["sub_queries"]) > 1:
                    merged_hits = []
                    for sq in transform_res["sub_queries"]:
                        hits = self.sparse_index.search(sq, top_k=top_k * FUSION_DEPTH_MULTIPLIER)
                        merged_hits.extend(hits)
                    return merged_hits
                return self.sparse_index.search(
                    search_query_text, top_k=top_k * FUSION_DEPTH_MULTIPLIER
                )
            return []

        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            future_dense = executor.submit(_do_dense)
            future_sparse = executor.submit(_do_sparse)

            try:
                dense_response = future_dense.result()
            except Exception as e:
                self.logger.error(f"RAG 稠密精排失败: {e}")
                result.rag_result_count = 0
                return

            try:
                sparse_hits = future_sparse.result()
            except Exception as e:
                self.logger.warning(f"BM25 稀疏召回失败: {e}")

        if self.sparse_index is not None and sparse_hits:
            response = self._fuse_with_sparse_hits(
                sparse_hits, filter_result, top_k, dense_response, result
            )
        else:
            response = dense_response
            response.results = response.results[:top_k]
            response.total_count = len(response.results)

        result.search_response = response
        result.rag_result_count = response.total_count

    def _fuse_with_sparse_hits(
        self,
        sparse_hits: List[tuple],
        filter_result: FilterResult,
        top_k: int,
        response: SearchResponse,
        result: HybridPipelineResult,
    ) -> SearchResponse:
        """用 RRF 融合稠密与已获取的 BM25 稀疏排名。"""
        dense_ranking = [r.vehicle.car_model for r in response.results]
        sparse_ranking = [model for model, _ in sparse_hits]

        if filter_result.car_models:
            allowed = set(filter_result.car_models)
            sparse_ranking = [m for m in sparse_ranking if m in allowed]

        result.sparse_result_count = len(sparse_ranking)
        weights = weights_for_query(result.matched_keywords, dynamic=self.dynamic_fusion_weights)
        result.fusion_weights = weights

        fused = reciprocal_rank_fusion(
            [dense_ranking, sparse_ranking],
            k=self.fusion_k,
            weights=weights.as_list(),
            top_k=top_k,
        )
        fused_order = {model: rank for rank, (model, _) in enumerate(fused)}

        reranked = [r for r in response.results if r.vehicle.car_model in fused_order]
        reranked.sort(key=lambda r: fused_order[r.vehicle.car_model])

        response.results = reranked[:top_k]
        response.total_count = len(response.results)
        return response

    def _fuse_with_sparse(
        self,
        query_text: str,
        filter_result: FilterResult,
        top_k: int,
        response: SearchResponse,
        result: HybridPipelineResult,
    ) -> SearchResponse:
        """用 RRF 融合稠密与 BM25 两路排名，按融合序重排 SearchResponse。"""
        dense_ranking = [r.vehicle.car_model for r in response.results]

        try:
            sparse_hits = self.sparse_index.search(
                query_text, top_k=top_k * FUSION_DEPTH_MULTIPLIER
            )
        except Exception as e:
            self.logger.warning(f"BM25 召回失败，退化为纯稠密: {e}")
            response.results = response.results[:top_k]
            response.total_count = len(response.results)
            return response

        sparse_ranking = [model for model, _ in sparse_hits]

        # 稀疏路不知道结构化过滤的存在，必须在这里施加同一个候选约束，
        # 否则被粗筛排除的车会通过融合重新回到结果里。
        if filter_result.car_models:
            allowed = set(filter_result.car_models)
            sparse_ranking = [m for m in sparse_ranking if m in allowed]

        result.sparse_result_count = len(sparse_ranking)

        # Route the weights on whether the rule parser found catalogue
        # vocabulary. A query naming "BMW" or "Mid-Size SUV" is on the lexical
        # channel's home ground; a paraphrase like "适合家用的车" gives BM25 no
        # exact token to grip, and the signal is entirely semantic.
        weights = weights_for_query(result.matched_keywords, dynamic=self.dynamic_fusion_weights)
        result.fusion_weights = weights

        fused = reciprocal_rank_fusion(
            [dense_ranking, sparse_ranking],
            k=self.fusion_k,
            weights=weights.as_list(),
            top_k=top_k,
        )
        fused_order = {model: rank for rank, (model, _) in enumerate(fused)}

        # 只有稠密路检索到的车才有 SearchResult 对象可用；稀疏路独有的车没有
        # 向量分数与匹配解释，无法凭空构造，因此融合在这里只重排而不引入新车。
        # （引入新车需要稀疏路也走一遍打分，属于下一步的优化。）
        reranked = [r for r in response.results if r.vehicle.car_model in fused_order]
        reranked.sort(key=lambda r: fused_order[r.vehicle.car_model])

        response.results = reranked[:top_k]
        response.total_count = len(response.results)
        return response

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


def build_default_pipeline(
    similarity_threshold: float = 0.3,
    price_tolerance: float = 0.2,
    enable_llm_parser: bool = True,
    enable_sparse: bool = True,
    llm_router=None,
) -> HybridPipeline:
    """
    装配一条开箱可用的混合检索管线。

    把嵌入模型、向量库、BM25 索引、SQLite 目录、规则/LLM 解析器一次性接好，供
    FastAPI 启动和评估脚本共用 —— 避免两处各自拼装导致参数漂移。

    Args:
        similarity_threshold: 语义相似度阈值。默认 0.3 而非 retriever 自身的 0.7：
            粗筛已经保证了结构化相关性，阈值过高会把召回打空。
        price_tolerance: 价格匹配容忍度
        enable_llm_parser: 规则引擎命中不足时是否允许 LLM 补充解析。
            无 LLM 凭据时 LLMParser.is_available() 返回 False，自动跳过。
        enable_sparse: 是否启用 BM25 稀疏路并做 RRF 融合。
        llm_parser 走 QUERY_PARSE 任务路由（本地优先）；传入共享的
            llm_router 可避免与 FastAPI 各建一个路由器。
    """
    # 局部导入：让 filter-only 的调用方（如 CI 的确定性门禁）无需加载嵌入模型
    from src.filter.llm_parser import LLMParser
    from src.rag.embeddings import BGEEmbeddingModel
    from src.rag.retriever import VehicleRetriever
    from src.rag.vector_store import ChromaVectorStore

    registry = LabelRegistry()
    db = VehicleDB(registry=registry)

    retriever = VehicleRetriever(
        BGEEmbeddingModel(),
        ChromaVectorStore(),
        similarity_threshold=similarity_threshold,
        price_tolerance=price_tolerance,
    )

    llm_parser = None
    if enable_llm_parser:
        try:
            from src.llm.router import Task, build_default_router

            router = llm_router or build_default_router()
            # 查询解析是控制路径：schema 约束、每次检索必调，路由到本地模型
            llm_parser = LLMParser(llm=router.bind(Task.QUERY_PARSE), registry=registry)
        except Exception:
            # 凭据缺失或 provider 不支持时静默降级为纯规则解析
            llm_parser = None

    sparse_index = None
    if enable_sparse:
        try:
            from src.retrieval.bm25_index import BM25Index

            sparse_index = BM25Index.load_or_build()
        except Exception as exc:
            # 稀疏索引缺失不该拖垮整条管线，降级为纯稠密
            get_logger(__name__).warning(f"BM25 索引不可用，降级为纯稠密检索: {exc}")

    return HybridPipeline(
        registry=registry,
        db=db,
        filter_engine=FilterEngine(db=db, registry=registry),
        query_parser=QueryParser(registry=registry),
        llm_parser=llm_parser,
        retriever=retriever,
        sparse_index=sparse_index,
    )
