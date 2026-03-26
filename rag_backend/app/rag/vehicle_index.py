"""
Vehicle knowledge index manager.

Provides a singleton-style accessor for the vehicle VectorStoreIndex,
handling both loading existing indexes and building new ones.
"""

import logging
from typing import Optional

from llama_index.core import VectorStoreIndex

from app.ingestion.index_builder import (
    get_chroma_client,
    get_chroma_vector_store,
    get_embedding_model,
    load_index,
)

logger = logging.getLogger(__name__)

# Module-level cache for the loaded index
_vehicle_index: Optional[VectorStoreIndex] = None


def get_vehicle_index(force_reload: bool = False) -> VectorStoreIndex:
    """
    Get the vehicle knowledge VectorStoreIndex.

    Loads from persistent ChromaDB on first call, then caches.
    If the index doesn't exist yet, raises an error suggesting
    to run the build script first.

    Args:
        force_reload: If True, reloads the index from disk.

    Returns:
        VectorStoreIndex for vehicle knowledge.

    Raises:
        RuntimeError: If no index exists in the persistent store.
    """
    global _vehicle_index

    if _vehicle_index is not None and not force_reload:
        return _vehicle_index

    try:
        chroma_client = get_chroma_client()
        vector_store = get_chroma_vector_store(chroma_client)
        embed_model = get_embedding_model()

        # Check if collection has data
        collection_name = vector_store._collection.name
        count = vector_store._collection.count()
        if count == 0:
            raise RuntimeError(
                f"ChromaDB collection '{collection_name}' is empty. "
                "Run 'python -m scripts.build_index' to build the index first."
            )

        _vehicle_index = load_index(embed_model, vector_store)
        logger.info(f"Loaded vehicle index with {count} documents.")
        return _vehicle_index

    except Exception as e:
        if isinstance(e, RuntimeError):
            raise
        raise RuntimeError(
            f"Failed to load vehicle index: {e}. "
            "Run 'python -m scripts.build_index' to build the index."
        ) from e


def reset_vehicle_index() -> None:
    """Clear the cached index (useful for testing)."""
    global _vehicle_index
    _vehicle_index = None
