"""
AutoVend Retrieval Module.
Provides Hybrid Pipeline (BM25 + Dense + RRF) and Parent-Child Document Retrieval.
"""

from src.retrieval.bm25_index import BM25Index
from src.retrieval.compression import CompressedContext, ContextCompressor
from src.retrieval.fusion import reciprocal_rank_fusion
from src.retrieval.hybrid_pipeline import HybridPipeline, HybridPipelineResult
from src.retrieval.parent_child_retriever import (
    ChildHit,
    ParentChildRetriever,
    ParentChildSearchResponse,
    ParentRetrievalResult,
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
    "HybridPipeline",
    "HybridPipelineResult",
    "reciprocal_rank_fusion",
    "ParentChildRetriever",
    "ParentChildSearchResponse",
    "ParentRetrievalResult",
    "ChildHit",
    "ContextCompressor",
    "CompressedContext",
    "QueryTransformationEngine",
    "TieredRetrievalEngine",
    "TieredSearchResult",
    "FastSpecIndex",
    "SemanticQueryCache",
]

