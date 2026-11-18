"""
RAG检索系统模块

包含数据加载、嵌入模型、向量存储、检索器等核心组件。
"""

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
