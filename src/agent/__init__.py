"""
AutoVend Sales Agent — Pure AI conversation logic.

This package is fully decoupled from the backend (FastAPI, storage, ChromaDB).
It depends only on: LLM interface, Pydantic schemas, LlamaIndex memory.

Entry point: SalesAgent / SalesOrchestrator
"""

from src.agent.orchestrator import SalesOrchestrator
from src.agent.sales_agent import SalesAgent

__all__ = ["SalesAgent", "SalesOrchestrator"]
