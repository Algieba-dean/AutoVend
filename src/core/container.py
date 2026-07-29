"""
Service Dependency Injection Container for AutoVend Architecture (src/core/container.py).

Provides a centralized service registry for managing singletons, RAG service instances,
Agent plugins, and DB interfaces without hardcoded cross-layer imports.
"""

import logging
from typing import Any, Dict, Optional

from src.core.interfaces import BaseRAGService

logger = logging.getLogger(__name__)


class ServiceContainer:
    """Central Dependency Injection Container for AutoVend Services."""

    _instances: Dict[str, Any] = {}
    _rag_service: Optional[BaseRAGService] = None

    @classmethod
    def register(cls, service_name: str, instance: Any) -> None:
        """Register a singleton service instance."""
        cls._instances[service_name] = instance
        logger.info(f"Registered service: {service_name}")

    @classmethod
    def get(cls, service_name: str, default: Any = None) -> Any:
        """Get registered service instance."""
        return cls._instances.get(service_name, default)

    @classmethod
    def register_rag_service(cls, rag_service: BaseRAGService) -> None:
        """Register global RAG service implementation."""
        cls._rag_service = rag_service
        cls._instances["rag_service"] = rag_service
        logger.info("Registered RAG Service implementation.")

    @classmethod
    def get_rag_service(cls) -> BaseRAGService:
        """Retrieve active RAG Service instance."""
        if cls._rag_service is None:
            # Lazy initialize default RAGService if not explicitly registered
            from src.rag_service.service import RAGService

            cls._rag_service = RAGService()
            cls._instances["rag_service"] = cls._rag_service
        return cls._rag_service

    @classmethod
    def reset(cls) -> None:
        """Reset container state (used in unit testing)."""
        cls._instances.clear()
        cls._rag_service = None
