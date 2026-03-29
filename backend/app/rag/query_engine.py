"""
Hybrid retrieval query engine for vehicle knowledge base.

Aligned with architecture "知识增强系统 RAG Engine":
- Path 1: Metadata Filter → exact-match database filtering
- Path 2: Embedding (bge-m3) → semantic similarity search
- Dual-path results merged → coarse Top-20 → Reranker → Top-3
"""

import logging
from typing import Any, Dict, List, Optional

from llama_index.core import VectorStoreIndex
from llama_index.core.schema import NodeWithScore
from llama_index.core.vector_stores import (
    FilterCondition,
    FilterOperator,
    MetadataFilter,
    MetadataFilters,
)

logger = logging.getLogger(__name__)

# Metadata fields that support exact-match filtering
FILTERABLE_FIELDS = {
    "brand",
    "prize",
    "powertrain_type",
    "vehicle_category_bottom",
    "design_style",
    "drive_type",
    "seat_layout",
    "autonomous_driving_level",
    "size",
    "family_friendliness",
    "comfort_level",
    "smartness",
    "energy_consumption_level",
}


def _build_metadata_filters(
    filters: Dict[str, str],
) -> Optional[MetadataFilters]:
    """
    Build LlamaIndex MetadataFilters from a dict of field→value pairs.

    Only includes fields that are in FILTERABLE_FIELDS and have non-empty values.

    Args:
        filters: Dict mapping metadata field names to desired values.

    Returns:
        MetadataFilters object, or None if no valid filters.
    """
    filter_list: List[MetadataFilter] = []
    for key, value in filters.items():
        if key in FILTERABLE_FIELDS and value:
            filter_list.append(
                MetadataFilter(
                    key=key,
                    value=value,
                    operator=FilterOperator.EQ,
                )
            )

    if not filter_list:
        return None

    return MetadataFilters(
        filters=filter_list,
        condition=FilterCondition.AND,
    )


def build_query_engine(
    index: VectorStoreIndex,
    similarity_top_k: int = 5,
    metadata_filters: Optional[Dict[str, str]] = None,
):
    """
    Build a query engine from a VectorStoreIndex with optional metadata filters.

    Args:
        index: The vehicle VectorStoreIndex.
        similarity_top_k: Number of top results to retrieve.
        metadata_filters: Optional dict of metadata field→value for filtering.

    Returns:
        A LlamaIndex query engine configured for retrieval.
    """
    filters = None
    if metadata_filters:
        filters = _build_metadata_filters(metadata_filters)

    retriever = index.as_retriever(
        similarity_top_k=similarity_top_k,
        filters=filters,
    )
    return retriever


def _deduplicate_results(
    results: List[NodeWithScore],
) -> List[NodeWithScore]:
    """
    Deduplicate retrieval results by car_model.

    When merging dual-path results, the same vehicle may appear
    in both paths. Keep the one with the higher score.
    """
    seen: Dict[str, NodeWithScore] = {}
    for node in results:
        model = node.metadata.get("car_model", id(node))
        existing = seen.get(model)
        if existing is None:
            seen[model] = node
        else:
            node_score = node.score or 0.0
            exist_score = existing.score or 0.0
            if node_score > exist_score:
                seen[model] = node
    return list(seen.values())


def dual_path_retrieve(
    index: VectorStoreIndex,
    semantic_query: str,
    metadata_filters: Optional[Dict[str, str]] = None,
    coarse_top_k: int = 20,
) -> List[NodeWithScore]:
    """
    Dual-path retrieval: metadata-filtered + pure semantic.

    Path 1: Metadata Filter path — exact-match pre-filtering
    Path 2: Semantic path — pure embedding similarity

    Results are merged and deduplicated to produce a coarse
    candidate set (Top-20) for the reranker.

    Args:
        index: The vehicle VectorStoreIndex.
        semantic_query: Clean query for embedding search.
        metadata_filters: Hard filters from structured extraction.
        coarse_top_k: Total candidates to return for reranking.

    Returns:
        Merged, deduplicated list of candidates.
    """
    half_k = max(coarse_top_k // 2, 3)

    # Path 1: Metadata-filtered retrieval
    filtered_results: List[NodeWithScore] = []
    if metadata_filters:
        try:
            filtered_retriever = build_query_engine(
                index, half_k, metadata_filters
            )
            filtered_results = filtered_retriever.retrieve(
                semantic_query
            )
            logger.info(
                f"Path 1 (metadata): {len(filtered_results)} results"
            )
        except Exception as e:
            logger.warning(f"Metadata-filtered retrieval failed: {e}")

    # Path 2: Pure semantic retrieval (no metadata filters)
    try:
        semantic_retriever = build_query_engine(index, half_k, None)
        semantic_results = semantic_retriever.retrieve(semantic_query)
        logger.info(
            f"Path 2 (semantic): {len(semantic_results)} results"
        )
    except Exception as e:
        logger.warning(f"Semantic retrieval failed: {e}")
        semantic_results = []

    # Merge and deduplicate
    merged = filtered_results + semantic_results
    deduped = _deduplicate_results(merged)

    # Sort by score descending
    deduped.sort(key=lambda n: n.score or 0.0, reverse=True)

    logger.info(
        f"Dual-path merged: {len(merged)} → "
        f"{len(deduped)} unique candidates"
    )

    return deduped[:coarse_top_k]


def retrieve_vehicles(
    index: VectorStoreIndex,
    query: str,
    metadata_filters: Optional[Dict[str, str]] = None,
    top_k: int = 5,
    user_needs: Optional[Dict[str, str]] = None,
    negative_filters: Optional[List[str]] = None,
) -> List[NodeWithScore]:
    """
    Full RAG retrieval pipeline with dual-path + reranking.

    Pipeline (aligned with 知识增强系统):
    1. Dual-path retrieval: metadata-filtered + pure semantic → Top-20
    2. Reranker: cross-attention scoring with negative filtering → Top-3

    Args:
        index: The vehicle VectorStoreIndex.
        query: Semantic query from query rewriter.
        metadata_filters: Hard filters from structured extraction.
        top_k: Final number of results to return.
        user_needs: Explicit needs for reranker boosting.
        negative_filters: Negative terms to penalize.

    Returns:
        List of NodeWithScore, reranked and filtered.
    """
    from app.rag.reranker import RerankConfig, rerank_with_cross_attention

    coarse_top_k = max(top_k * 4, 20)

    logger.info(
        f"RAG pipeline: query='{query[:80]}', "
        f"filters={metadata_filters}, "
        f"negatives={negative_filters}"
    )

    # Step 1: Dual-path coarse retrieval
    candidates = dual_path_retrieve(
        index, query, metadata_filters, coarse_top_k
    )

    # Step 2: Reranker (cross-attention scoring)
    config = RerankConfig(top_k=top_k)
    results = rerank_with_cross_attention(
        candidates,
        query,
        user_needs=user_needs or {},
        negative_filters=negative_filters or [],
        config=config,
    )

    logger.info(
        f"RAG pipeline complete: "
        f"{len(candidates)} candidates → {len(results)} results"
    )
    for i, node in enumerate(results):
        car_model = node.metadata.get("car_model", "Unknown")
        logger.debug(
            f"  [{i + 1}] {car_model} "
            f"(score={node.score:.4f})"
        )

    return results


def format_retrieval_results(
    results: List[NodeWithScore],
) -> List[Dict[str, Any]]:
    """
    Format retrieval results into a structured list for API responses.

    Args:
        results: List of NodeWithScore from retrieve_vehicles.

    Returns:
        List of dicts with car_model, score, metadata, and text_snippet.
    """
    formatted = []
    for node in results:
        formatted.append(
            {
                "car_model": node.metadata.get("car_model", "Unknown"),
                "score": round(node.score, 4) if node.score is not None else None,
                "metadata": {k: v for k, v in node.metadata.items() if k != "source_file"},
                "text_snippet": node.text[:300] if node.text else "",
            }
        )
    return formatted
