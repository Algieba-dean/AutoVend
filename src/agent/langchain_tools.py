"""
LangChain `@tool` definitions for the AutoVend LangGraph sales agent.

Keeps strict package isolation (no imports from `backend`, `fastapi`, or `chromadb`).
Delegates RAG retrieval to `ServiceContainer.get_rag_service()` (backed by
LlamaIndex + HybridPipeline).
"""

import json
from typing import Any, Dict, List, Optional

from langchain_core.tools import tool
from pydantic import BaseModel, Field

from src.core.container import ServiceContainer
from src.core.interfaces import RAGQueryRequest


class VehicleSearchInput(BaseModel):
    query: str = Field(..., description="Natural language vehicle search query")
    brand: Optional[str] = Field(default=None, description="Preferred vehicle brand")
    price: Optional[str] = Field(default=None, description="Budget range, e.g. '20万~30万'")
    power_type: Optional[str] = Field(default=None, description="Powertrain type (纯电/增程/插混/燃油)")
    top_k: int = Field(default=5, ge=1, le=20, description="Max number of candidates to return")


@tool("search_vehicles", args_schema=VehicleSearchInput)
def search_vehicles_tool(
    query: str,
    brand: Optional[str] = None,
    price: Optional[str] = None,
    power_type: Optional[str] = None,
    top_k: int = 5,
) -> str:
    """Search candidate vehicles using AutoVend's LlamaIndex + Hybrid RAG service."""
    rag_service = ServiceContainer.get_rag_service()
    if rag_service is None:
        return json.dumps({"results": [], "error": "RAGService not registered"}, ensure_ascii=False)

    explicit: Dict[str, Any] = {}
    if brand:
        explicit["brand"] = brand
    if price:
        explicit["price"] = price
    if power_type:
        explicit["powertrain_type"] = power_type

    req = RAGQueryRequest(query_text=query, explicit_conditions=explicit, top_k=top_k)
    resp = rag_service.search_vehicles(req)
    return json.dumps(
        {
            "total_count": resp.total_count,
            "latency_ms": resp.latency_ms,
            "results": resp.results[:top_k],
        },
        ensure_ascii=False,
    )


@tool("get_vehicle_detail")
def get_vehicle_detail_tool(car_model: str) -> str:
    """Retrieve structured specifications for a specific car model."""
    rag_service = ServiceContainer.get_rag_service()
    if rag_service is None:
        return json.dumps({"error": "RAGService not registered"}, ensure_ascii=False)
    detail = rag_service.get_vehicle_detail(car_model)
    return json.dumps(detail or {"car_model": car_model, "found": False}, ensure_ascii=False)


@tool("validate_test_drive_slot")
def validate_test_drive_slot_tool(
    reservation_date: Optional[str] = None,
    reservation_time: Optional[str] = None,
    reservation_location: Optional[str] = None,
    test_driver: Optional[str] = None,
    phone_number: Optional[str] = None,
) -> str:
    """Validate completeness of 4S test-drive reservation fields."""
    missing: List[str] = []
    if not reservation_date:
        missing.append("reservation_date")
    if not reservation_time:
        missing.append("reservation_time")
    if not reservation_location:
        missing.append("reservation_location")
    if not test_driver:
        missing.append("test_driver")
    if not phone_number:
        missing.append("phone_number")
    return json.dumps({"valid": len(missing) == 0, "missing_fields": missing}, ensure_ascii=False)


def get_autovend_tools():
    """Return the standard list of LangChain tools for the AutoVend agent."""
    return [search_vehicles_tool, get_vehicle_detail_tool, validate_test_drive_slot_tool]
