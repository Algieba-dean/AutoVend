"""
Standalone RAG Service package for AutoVend.
"""

from src.rag_service.onnx_reranker import OnnxCrossEncoderReranker
from src.rag_service.reranker import RankRefiner, calculate_gaussian_price_fit
from src.rag_service.schemas import (
    SpecCompareRequest,
    SpecCompareResponse,
    VehicleQueryRequest,
    VehicleQueryResponse,
    VehicleSearchResult,
)
from src.rag_service.service import RAGService

__all__ = [
    "RAGService",
    "RankRefiner",
    "OnnxCrossEncoderReranker",
    "calculate_gaussian_price_fit",
    "VehicleQueryRequest",
    "VehicleQueryResponse",
    "VehicleSearchResult",
    "SpecCompareRequest",
    "SpecCompareResponse",
]
