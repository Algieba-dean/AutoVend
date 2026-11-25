"""
RAG检索系统模块

包含数据加载、嵌入模型、向量存储、检索器等核心组件。
"""

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .data_loader import VehicleDataLoader
    from .embeddings import BGEEmbeddingModel, EmbeddingDegradedError, EmbeddingInferenceError
    from .index_builder import IndexBuilder, IndexDLQ
    from .pgvector_store import PgVectorStore
    from .retriever import VehicleRetriever
    from .vector_store import (
        ChromaVectorStore,
        create_vector_store,
        extract_vehicle_trim,
        generate_vehicle_doc_id,
        get_vector_store,
    )

__all__ = [
    "VehicleDataLoader",
    "BGEEmbeddingModel",
    "EmbeddingInferenceError",
    "EmbeddingDegradedError",
    "PgVectorStore",
    "ChromaVectorStore",
    "create_vector_store",
    "get_vector_store",
    "VehicleRetriever",
    "IndexBuilder",
    "IndexDLQ",
    "generate_vehicle_doc_id",
    "extract_vehicle_trim",
]


def __getattr__(name: str) -> Any:
    if name == "VehicleDataLoader":
        from .data_loader import VehicleDataLoader

        return VehicleDataLoader
    if name in ("BGEEmbeddingModel", "EmbeddingInferenceError", "EmbeddingDegradedError"):
        from . import embeddings

        return getattr(embeddings, name)
    if name == "PgVectorStore":
        from .pgvector_store import PgVectorStore

        return PgVectorStore
    if name in (
        "ChromaVectorStore",
        "create_vector_store",
        "get_vector_store",
        "generate_vehicle_doc_id",
        "extract_vehicle_trim",
    ):
        from . import vector_store

        return getattr(vector_store, name)
    if name == "VehicleRetriever":
        from .retriever import VehicleRetriever

        return VehicleRetriever
    if name in ("IndexBuilder", "IndexDLQ"):
        from . import index_builder

        return getattr(index_builder, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
