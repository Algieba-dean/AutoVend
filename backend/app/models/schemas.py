"""
Pydantic data models for AutoVend RAG Backend.

Domain models (Stage, UserProfile, VehicleNeeds, etc.) are canonical in
agent.schemas and re-exported here for backward compatibility.
API-specific request/response models (ChatRequest, TestDriveRequest, etc.)
live here because they are backend concerns.
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

# ── Re-export domain models from agent.schemas ─────────────────
from agent.schemas import (  # noqa: F401
    ExplicitNeeds,
    ImplicitNeeds,
    ReservationInfo,
    Stage,
    StageInfo,
    UserProfile,
    VehicleNeeds,
)

# --- Chat (API-specific) ---


class ChatMessage(BaseModel):
    """A single chat message."""

    message_id: str = ""
    sender_type: str = "user"
    sender_id: str = ""
    content: str = ""
    timestamp: str = ""
    status: str = "delivered"


class ChatRequest(BaseModel):
    """Request body for sending a chat message."""

    session_id: str
    message: str
    profile: Optional[UserProfile] = None


class ChatResponse(BaseModel):
    """Response body for a chat message."""

    message: ChatMessage
    response: ChatMessage
    stage: StageInfo
    profile: UserProfile
    needs: VehicleNeeds
    matched_car_models: List[Dict[str, Any]] = Field(default_factory=list)
    reservation_info: ReservationInfo = Field(default_factory=ReservationInfo)


class SessionCreateRequest(BaseModel):
    """Request body for creating a new session."""

    phone_number: str = ""
    profile: Optional[UserProfile] = None


class SessionCreateResponse(BaseModel):
    """Response body for session creation."""

    session_id: str
    message: str = "Session created successfully."
    stage: StageInfo = Field(default_factory=StageInfo)
    profile: UserProfile = Field(default_factory=UserProfile)


# --- Test Drive (API-specific) ---


class TestDriveRequest(BaseModel):
    """Request body for creating/updating a test drive reservation."""

    phone_number: str
    test_driver: str = ""
    reservation_date: str = ""
    reservation_time: str = ""
    reservation_location: str = ""
    salesman: str = ""
    car_model: str = ""


class TestDriveResponse(BaseModel):
    """Response body for test drive operations."""

    phone_number: str
    reservation: ReservationInfo
    car_model: str = ""
    created_at: str = ""
