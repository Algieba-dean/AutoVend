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


def retrieve_vehicles(
    index: VectorStoreIndex,
    query: str,
    metadata_filters: Optional[Dict[str, str]] = None,
    top_k: int = 5,
) -> List[NodeWithScore]:
    """
    Retrieve relevant vehicles using semantic search + metadata filtering.

    This is the main retrieval function. It combines:
    1. Semantic similarity: query text is embedded and compared against vehicle docs.
    2. Metadata filtering: exact-match filters on structured fields (brand, price, etc.)

    Args:
        index: The vehicle VectorStoreIndex.
        query: Natural language query describing desired vehicle characteristics.
        metadata_filters: Optional dict of metadata field→value for pre-filtering.
        top_k: Number of top results to return.

    Returns:
        List of NodeWithScore objects, sorted by relevance score (descending).
    """
    retriever = build_query_engine(index, top_k, metadata_filters)

    logger.info(
        f"Retrieving vehicles: query='{query[:80]}...', "
        f"top_k={top_k}, filters={metadata_filters}"
    )

    results = retriever.retrieve(query)

    logger.info(f"Retrieved {len(results)} vehicles.")
    for i, node in enumerate(results):
        car_model = node.metadata.get("car_model", "Unknown")
        logger.debug(f"  [{i+1}] {car_model} (score={node.score:.4f})")

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
        formatted.append({
            "car_model": node.metadata.get("car_model", "Unknown"),
            "score": round(node.score, 4) if node.score is not None else None,
            "metadata": {
                k: v
                for k, v in node.metadata.items()
                if k != "source_file"
            },
            "text_snippet": node.text[:300] if node.text else "",
        })
    return formatted
