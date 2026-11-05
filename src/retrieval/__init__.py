"""
AutoVend Retrieval Module.
Provides Hybrid Pipeline (BM25 + Dense + RRF) and Parent-Child Document Retrieval.
"""

from src.retrieval.bm25_index import BM25Index, SQLiteFTS5Index
from src.retrieval.compression import CompressedContext, ContextCompressor
from src.retrieval.fusion import reciprocal_rank_fusion
from src.retrieval.hybrid_pipeline import HybridPipeline, HybridPipelineResult
from src.retrieval.parent_child_retriever import (
    ChildHit,
    ParentChildRetriever,
    ParentChildSearchResponse,
    ParentRetrievalResult,
    format_isolated_llm_context,
    retrieve_multi_vehicle_context,
    vectorized_cosine_search,
)
from src.retrieval.query_transform import QueryTransformationEngine
from src.retrieval.tiered_engine import (
    FastSpecIndex,
    SemanticQueryCache,
    TieredRetrievalEngine,
    TieredSearchResult,
)

__all__ = [
    "BM25Index",
    "SQLiteFTS5Index",
    "HybridPipeline",
    "HybridPipelineResult",
    "reciprocal_rank_fusion",
    "ParentChildRetriever",
    "ParentChildSearchResponse",
    "ParentRetrievalResult",
    "ChildHit",
    "vectorized_cosine_search",
    "retrieve_multi_vehicle_context",
    "format_isolated_llm_context",
    "ContextCompressor",
    "CompressedContext",
    "QueryTransformationEngine",
    "TieredRetrievalEngine",
    "TieredSearchResult",
    "FastSpecIndex",
    "SemanticQueryCache",
]

