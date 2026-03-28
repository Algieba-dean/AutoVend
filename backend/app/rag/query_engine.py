"""
Hybrid retrieval query engine for vehicle knowledge base.

Combines semantic similarity search with metadata filtering to find
the most relevant vehicles based on user needs.
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


def rerank_results(
    results: List[NodeWithScore],
    user_needs: Optional[Dict[str, str]] = None,
    top_k: int = 5,
) -> List[NodeWithScore]:
    """
    Rerank retrieval results using metadata-based scoring.

    Applies a lightweight reranking that boosts results whose metadata
    fields match the user's stated needs. This compensates for cases
    where semantic similarity alone doesn't capture exact parameter matches.

    Args:
        results: Initial retrieval results.
        user_needs: Dict of explicit need field→value for boosting.
        top_k: Number of results to return after reranking.

    Returns:
        Reranked and truncated list of NodeWithScore.
    """
    if not user_needs or not results:
        return results[:top_k]

    scored = []
    for node in results:
        bonus = 0.0
        meta = node.metadata
        for key, value in user_needs.items():
            if not value:
                continue
            meta_val = str(meta.get(key, "")).lower()
            need_val = str(value).lower()
            if meta_val and need_val:
                if need_val in meta_val or meta_val in need_val:
                    bonus += 0.05  # Boost for each matching field
        # Create a new score combining semantic + metadata match
        original_score = node.score if node.score is not None else 0.0
        node.score = original_score + bonus
        scored.append(node)

    scored.sort(key=lambda n: n.score or 0, reverse=True)
    logger.debug(
        f"Reranked {len(results)} results with {len(user_needs)} need fields, returning top {top_k}"
    )
    return scored[:top_k]


def retrieve_vehicles(
    index: VectorStoreIndex,
    query: str,
    metadata_filters: Optional[Dict[str, str]] = None,
    top_k: int = 5,
    user_needs: Optional[Dict[str, str]] = None,
) -> List[NodeWithScore]:
    """
    Retrieve relevant vehicles using semantic search + metadata filtering + reranking.

    Pipeline:
    1. Semantic similarity: query text is embedded and compared against vehicle docs.
    2. Metadata filtering: exact-match filters on structured fields (brand, price, etc.)
    3. Reranking: metadata-based boosting to improve precision on exact parameter matches.

    Args:
        index: The vehicle VectorStoreIndex.
        query: Natural language query describing desired vehicle characteristics.
        metadata_filters: Optional dict of metadata field→value for pre-filtering.
        top_k: Number of top results to return.
        user_needs: Optional dict of user's explicit needs for reranking boost.

    Returns:
        List of NodeWithScore objects, sorted by relevance score (descending).
    """
    # Over-retrieve for reranking: fetch 2x candidates
    fetch_k = top_k * 2 if user_needs else top_k
    retriever = build_query_engine(index, fetch_k, metadata_filters)

    logger.info(
        f"Retrieving vehicles: query='{query[:80]}...', top_k={top_k}, "
        f"fetch_k={fetch_k}, filters={metadata_filters}"
    )

    results = retriever.retrieve(query)

    # Rerank if user needs are provided
    if user_needs:
        results = rerank_results(results, user_needs, top_k)
    else:
        results = results[:top_k]

    logger.info(f"Retrieved {len(results)} vehicles (after reranking).")
    for i, node in enumerate(results):
        car_model = node.metadata.get("car_model", "Unknown")
        logger.debug(f"  [{i + 1}] {car_model} (score={node.score:.4f})")

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
