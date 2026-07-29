"""
Data schemas for the Standalone RAG Service (src/rag_service).
Defines protocol boundaries for RAG requests, responses, and spec comparisons.
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class VehicleQueryRequest(BaseModel):
    """Request payload for vehicle retrieval."""

    query_text: str = Field(..., description="Natural language search query")
    explicit_needs: Optional[Dict[str, Any]] = Field(
        default=None, description="Explicit structured needs"
    )
    implicit_needs: Optional[Dict[str, Any]] = Field(
        default=None, description="Implicit preference labels"
    )
    top_k: int = Field(default=5, ge=1, le=50, description="Number of candidate vehicles to return")
    enable_rerank: bool = Field(
        default=True, description="Enable Cross-Encoder reranking / refinement"
    )


class VehicleSearchResult(BaseModel):
    """Single vehicle search result item."""

    car_model: str
    score: float
    brand: str = ""
    price: str = ""
    category: str = ""
    powertrain_type: str = ""
    metadata: Dict[str, Any] = Field(default_factory=dict)
    text_snippet: str = ""
    key_features: List[str] = Field(default_factory=list)


class VehicleQueryResponse(BaseModel):
    """Response payload for vehicle retrieval."""

    results: List[VehicleSearchResult] = Field(default_factory=list)
    candidate_count: int = 0
    degrade_level: int = 0
    total_time_ms: float = 0.0
    search_summary: Dict[str, Any] = Field(default_factory=dict)


class SpecCompareRequest(BaseModel):
    """Request to compare specs of two or more vehicle models."""

    car_models: List[str] = Field(..., min_length=2, description="List of car models to compare")
    target_features: Optional[List[str]] = Field(
        default=None,
        description="Specific feature categories to compare (e.g. price, powertrain, safety)",
    )


class SpecDiffItem(BaseModel):
    """Single feature row in side-by-side spec comparison."""

    feature_name: str
    values: Dict[str, str]  # {car_model_name: value_str}


class SpecCompareResponse(BaseModel):
    """Side-by-side comparison matrix result."""

    car_models: List[str]
    diff_matrix: List[SpecDiffItem] = Field(default_factory=list)
    comparison_summary: str = ""
