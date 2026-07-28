"""
Core Domain Interfaces for AutoVend Architecture (src/core/interfaces.py).

Defines clean abstraction contracts for RAG Service, Agent Plugins, Data Ingestion, and LLM providers.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from pydantic import BaseModel


class RAGQueryRequest(BaseModel):
    """Unified query request for RAG domain."""

    query_text: str
    top_k: int = 10
    explicit_conditions: Dict[str, Any] = {}
    implicit_needs: Dict[str, Any] = {}
    session_id: Optional[str] = None


class RAGQueryResponse(BaseModel):
    """Unified response from RAG domain."""

    results: List[Dict[str, Any]] = []
    total_count: int = 0
    candidate_count: int = 0
    latency_ms: float = 0.0
    degrade_level: int = 0


class BaseRAGService(ABC):
    """Abstract interface for vehicle RAG search services."""

    @abstractmethod
    def search_vehicles(self, request: RAGQueryRequest) -> RAGQueryResponse:
        """Search vehicles based on natural language query and context."""
        pass

    @abstractmethod
    def get_vehicle_detail(self, car_model: str) -> Optional[Dict[str, Any]]:
        """Retrieve detailed specs for a specific car model."""
        pass


class BaseAgentPlugin(ABC):
    """Abstract interface for Agent processing middleware plugins."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Plugin identifier name."""
        pass

    @abstractmethod
    def process_before_response(self, state: Any, context: Dict[str, Any]) -> None:
        """Middleware hook executed before Agent generates response."""
        pass

    @abstractmethod
    def process_after_response(self, response_text: str, context: Dict[str, Any]) -> str:
        """Middleware hook executed after response generation for reflection & guardrails."""
        pass
