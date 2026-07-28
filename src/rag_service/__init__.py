"""
Standalone RAG Service package for AutoVend.
"""

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
    "VehicleQueryRequest",
    "VehicleQueryResponse",
    "VehicleSearchResult",
    "SpecCompareRequest",
    "SpecCompareResponse",
]
