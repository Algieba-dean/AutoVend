"""
Retrieval systems under evaluation.

Each system is a callable `(query_text, top_k) -> List[car_model]`, ranked best
first. Wrapping them behind one interface is what makes the A/B honest: every
variant sees the same golden set, the same k, and the same scoring code.

Variants:

- ``filter``   structured SQLite pre-filter only, no ranking model. The floor.
- ``dense``    vector search over the whole catalogue (the "pure RAG" baseline).
- ``bm25``     lexical BM25 over the whole catalogue.
- ``hybrid``   structured pre-filter -> dense rerank. The pipeline as shipped.
- ``fusion``   structured pre-filter -> dense + BM25 -> RRF. The proposed path.
"""

from typing import Callable, Dict, List, Optional

SystemFn = Callable[[str, int], List[str]]

#: Systems that need neither the embedding model nor the vector index, so they
#: can run in a seconds-long CI job.
LIGHTWEIGHT_SYSTEMS = ("filter", "bm25")

ALL_SYSTEMS = ("filter", "dense", "bm25", "hybrid", "fusion")


def build_system(name: str, top_k_multiplier: int = 1) -> SystemFn:
    """
    Construct one retrieval system by name.

    Imports are local so that asking for `filter` or `bm25` never drags in
    torch and the 2GB embedding model.
    """
    if name == "filter":
        return _build_filter()
    if name == "dense":
        return _build_dense()
    if name == "bm25":
        return _build_bm25()
    if name == "hybrid":
        return _build_hybrid(use_fusion=False)
    if name == "fusion":
        return _build_hybrid(use_fusion=True)
    raise ValueError(f"Unknown retrieval system: {name!r}. Expected one of {ALL_SYSTEMS}.")


def _build_filter() -> SystemFn:
    from src.filter.filter_engine import FilterEngine
    from src.filter.label_registry import LabelRegistry
    from src.filter.query_parser import QueryParser
    from src.filter.vehicle_db import VehicleDB

    registry = LabelRegistry()
    db = VehicleDB(registry=registry)
    engine = FilterEngine(db=db, registry=registry)
    parser = QueryParser(registry=registry)

    def run(query_text: str, top_k: int) -> List[str]:
        parsed = parser.parse(query_text)
        result = engine.filter(parsed.conditions)
        # The filter has no ranking signal — take candidates in catalogue order.
        # Any apparent precision it shows is structural, not learned.
        return result.car_models[:top_k]

    return run


def _build_dense() -> SystemFn:
    from src.models.query import Query
    from src.rag.embeddings import BGEEmbeddingModel
    from src.rag.retriever import VehicleRetriever
    from src.rag.vector_store import ChromaVectorStore

    retriever = VehicleRetriever(BGEEmbeddingModel(), ChromaVectorStore(), similarity_threshold=0.0)

    def run(query_text: str, top_k: int) -> List[str]:
        response = retriever.search(Query(text=query_text, top_k=top_k))
        return [r.vehicle.car_model for r in response.results]

    return run


def _build_bm25() -> SystemFn:
    from src.retrieval.bm25_index import BM25Index

    index = BM25Index.load_or_build()

    def run(query_text: str, top_k: int) -> List[str]:
        return [model for model, _ in index.search(query_text, top_k=top_k)]

    return run


def _build_hybrid(use_fusion: bool) -> SystemFn:
    from src.retrieval.hybrid_pipeline import build_default_pipeline

    pipeline = build_default_pipeline(
        similarity_threshold=0.0,
        enable_llm_parser=False,  # keep the evaluation deterministic
        enable_sparse=use_fusion,
    )

    def run(query_text: str, top_k: int) -> List[str]:
        result = pipeline.search(query_text, top_k=top_k, use_llm_fallback=False)
        response = result.search_response
        if response is None:
            return []
        return [r.vehicle.car_model for r in response.results]

    return run


def build_systems(names: Optional[List[str]] = None) -> Dict[str, SystemFn]:
    """Build several systems, keeping the requested order."""
    return {name: build_system(name) for name in (names or list(ALL_SYSTEMS))}
