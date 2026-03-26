"""
Pydantic data models for AutoVend RAG Backend.

Defines schemas for user profiles, vehicle needs (explicit/implicit),
reservation info, chat sessions, and stage management.
All models are compatible with the existing frontend API contract.
"""

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# --- Stage ---

class Stage(str, Enum):
    """Conversation stage enumeration."""
    WELCOME = "welcome"
    PROFILE_ANALYSIS = "profile_analysis"
    NEEDS_ANALYSIS = "needs_analysis"
    CAR_SELECTION = "car_selection_confirmation"
    RESERVATION_4S = "reservation4s"
    RESERVATION_CONFIRMATION = "reservation_confirmation"
    FAREWELL = "farewell"


class StageInfo(BaseModel):
    """Stage transition info."""
    previous_stage: str = ""
    current_stage: str = Stage.WELCOME.value


# --- User Profile ---

class UserProfile(BaseModel):
    """User profile extracted from conversation."""
    phone_number: str = ""
    name: str = ""
    title: str = ""
    age: str = ""
    target_driver: str = ""
    expertise: str = ""
    family_size: str = ""
    price_sensitivity: str = ""
    residence: str = ""
    parking_conditions: str = ""


# --- Vehicle Needs ---

class ExplicitNeeds(BaseModel):
    """Explicit needs directly stated by the user."""
    prize: str = ""
    vehicle_category_bottom: str = ""
    brand: str = ""
    powertrain_type: str = ""
    design_style: str = ""
    drive_type: str = ""
    seat_layout: str = ""
    autonomous_driving_level: str = ""
    ABS: str = ""
    ESP: str = ""
    airbag_count: str = ""
    horsepower: str = ""
    torque: str = ""
    acceleration_0_100: str = ""
    max_speed: str = ""
    fuel_consumption: str = ""
    electric_range: str = ""
    battery_capacity: str = ""
    cargo_volume: str = ""
    wheelbase: str = ""
    ground_clearance: str = ""


class ImplicitNeeds(BaseModel):
    """Implicit needs inferred from user profile and conversation context."""
    size: str = ""
    vehicle_usability: str = ""
    aesthetics: str = ""
    comfort_level: str = ""
    smartness: str = ""
    family_friendliness: str = ""
    energy_consumption_level: str = ""
    road_performance: str = ""
    brand_grade: str = ""
    driving_range: str = ""
    power_performance: str = ""
    safety: str = ""
    cost_performance: str = ""
    space: str = ""
    cargo_space: str = ""


class VehicleNeeds(BaseModel):
    """Combined explicit and implicit vehicle needs."""
    explicit: ExplicitNeeds = Field(default_factory=ExplicitNeeds)
    implicit: ImplicitNeeds = Field(default_factory=ImplicitNeeds)


# --- Reservation ---

class ReservationInfo(BaseModel):
    """Test drive reservation information."""
    test_driver: str = ""
    reservation_date: str = ""
    reservation_time: str = ""
    reservation_location: str = ""
    reservation_phone_number: str = ""
    salesman: str = ""


# --- Chat ---

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


# --- Test Drive ---

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
