"""
Agent-level schemas — the protocol boundary between Agent and Backend.

All domain models (Stage, UserProfile, VehicleNeeds, etc.) live here.
The backend imports these; the agent uses them internally.
Neither package imports from the other's internal modules.
"""

from enum import Enum
from typing import Any, Dict, List

from pydantic import BaseModel, Field

# ── Stage ──────────────────────────────────────────────────────


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
    """Stage transition info included in API responses."""

    previous_stage: str = ""
    current_stage: str = Stage.WELCOME.value


# ── User Profile ───────────────────────────────────────────────


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


# ── Vehicle Needs ──────────────────────────────────────────────


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


# ── Reservation ────────────────────────────────────────────────


class ReservationInfo(BaseModel):
    """Test drive reservation information."""

    test_driver: str = ""
    reservation_date: str = ""
    reservation_time: str = ""
    reservation_location: str = ""
    reservation_phone_number: str = ""
    salesman: str = ""


# ── Agent Protocol ─────────────────────────────────────────────


class SessionState(BaseModel):
    """
    Serializable snapshot of all session-level state.
    Passed in and out of the Agent on every turn.
    """

    session_id: str = ""
    stage: Stage = Stage.WELCOME
    previous_stage: str = ""
    profile: UserProfile = Field(default_factory=UserProfile)
    needs: VehicleNeeds = Field(default_factory=VehicleNeeds)
    matched_cars: List[Dict[str, Any]] = Field(default_factory=list)
    reservation: ReservationInfo = Field(default_factory=ReservationInfo)
    rewrite_result: Any = None


class AgentInput(BaseModel):
    """
    Everything the Agent needs to process one conversation turn.

    The backend is responsible for:
    - Managing session lifecycle
    - Running RAG retrieval and passing results as `retrieved_cars`
    - Serializing/deserializing SessionState
    """

    session_state: SessionState
    user_message: str
    retrieved_cars: List[Dict[str, Any]] = Field(default_factory=list)


class AgentResult(BaseModel):
    """
    Everything the Agent returns after processing one turn.

    The backend uses this to:
    - Update stored session state
    - Build the API response
    """

    session_state: SessionState
    response_text: str = ""
    stage_changed: bool = False
