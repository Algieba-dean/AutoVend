"""
KPI Test Suite — Stage Transition Correctness.

Tests that the conversation stage machine transitions correctly
under a variety of scenarios (happy path + edge cases).

KPI Targets:
  - Happy-path stage transition correctness: 100%
  - Edge-case stage transition correctness: ≥ 95%
"""

import pytest

from agent.schemas import (
    ExplicitNeeds,
    ReservationInfo,
    Stage,
    UserProfile,
    VehicleNeeds,
)
from agent.stages import determine_next_stage

# ── Happy Path: Full Journey ───────────────────────────────────
# Simulates a complete user journey from welcome → farewell.

HAPPY_PATH_STEPS = [
    {
        "id": "HP01",
        "description": "Welcome → Profile Analysis (always advances)",
        "current": Stage.WELCOME,
        "profile": UserProfile(),
        "needs": VehicleNeeds(),
        "cars": [],
        "reservation": ReservationInfo(),
        "expected": Stage.PROFILE_ANALYSIS,
    },
    {
        "id": "HP02",
        "description": "Profile Analysis → Needs Analysis (name collected)",
        "current": Stage.PROFILE_ANALYSIS,
        "profile": UserProfile(name="Alice", age="30"),
        "needs": VehicleNeeds(),
        "cars": [],
        "reservation": ReservationInfo(),
        "expected": Stage.NEEDS_ANALYSIS,
    },
    {
        "id": "HP03",
        "description": "Needs Analysis → Car Selection (2+ fields filled)",
        "current": Stage.NEEDS_ANALYSIS,
        "profile": UserProfile(name="Alice"),
        "needs": VehicleNeeds(explicit=ExplicitNeeds(brand="Tesla", powertrain_type="EV")),
        "cars": [],
        "reservation": ReservationInfo(),
        "expected": Stage.CAR_SELECTION,
    },
    {
        "id": "HP04",
        "description": "Car Selection → Reservation 4S (cars matched)",
        "current": Stage.CAR_SELECTION,
        "profile": UserProfile(name="Alice"),
        "needs": VehicleNeeds(),
        "cars": [{"car_model": "Tesla Model Y", "score": 0.95}],
        "reservation": ReservationInfo(),
        "expected": Stage.RESERVATION_4S,
    },
    {
        "id": "HP05",
        "description": "Reservation 4S → Confirmation (date+time+location)",
        "current": Stage.RESERVATION_4S,
        "profile": UserProfile(name="Alice"),
        "needs": VehicleNeeds(),
        "cars": [],
        "reservation": ReservationInfo(
            reservation_date="2024-06-01",
            reservation_time="10:00",
            reservation_location="East Store",
        ),
        "expected": Stage.RESERVATION_CONFIRMATION,
    },
    {
        "id": "HP06",
        "description": "Confirmation → Farewell (all reservation fields)",
        "current": Stage.RESERVATION_CONFIRMATION,
        "profile": UserProfile(name="Alice"),
        "needs": VehicleNeeds(),
        "cars": [],
        "reservation": ReservationInfo(
            test_driver="Alice",
            reservation_date="2024-06-01",
            reservation_time="10:00",
            reservation_location="East Store",
            reservation_phone_number="13800138000",
        ),
        "expected": Stage.FAREWELL,
    },
]

# ── Edge Cases ─────────────────────────────────────────────────

EDGE_CASE_STEPS = [
    {
        "id": "EC01",
        "description": "Profile stays if no info provided",
        "current": Stage.PROFILE_ANALYSIS,
        "profile": UserProfile(),
        "needs": VehicleNeeds(),
        "cars": [],
        "reservation": ReservationInfo(),
        "expected": Stage.PROFILE_ANALYSIS,
    },
    {
        "id": "EC02",
        "description": "Needs stays if only 1 field filled",
        "current": Stage.NEEDS_ANALYSIS,
        "profile": UserProfile(),
        "needs": VehicleNeeds(explicit=ExplicitNeeds(brand="BMW")),
        "cars": [],
        "reservation": ReservationInfo(),
        "expected": Stage.NEEDS_ANALYSIS,
    },
    {
        "id": "EC03",
        "description": "Car selection stays if no matched cars",
        "current": Stage.CAR_SELECTION,
        "profile": UserProfile(),
        "needs": VehicleNeeds(),
        "cars": [],
        "reservation": ReservationInfo(),
        "expected": Stage.CAR_SELECTION,
    },
    {
        "id": "EC04",
        "description": "Reservation stays if incomplete (only date)",
        "current": Stage.RESERVATION_4S,
        "profile": UserProfile(),
        "needs": VehicleNeeds(),
        "cars": [],
        "reservation": ReservationInfo(reservation_date="2024-06-01"),
        "expected": Stage.RESERVATION_4S,
    },
    {
        "id": "EC05",
        "description": "Confirmation stays if no phone number",
        "current": Stage.RESERVATION_CONFIRMATION,
        "profile": UserProfile(),
        "needs": VehicleNeeds(),
        "cars": [],
        "reservation": ReservationInfo(
            test_driver="Alice",
            reservation_date="2024-06-01",
            reservation_time="10:00",
            reservation_location="Store",
        ),
        "expected": Stage.RESERVATION_CONFIRMATION,
    },
    {
        "id": "EC06",
        "description": "Farewell is terminal — stays forever",
        "current": Stage.FAREWELL,
        "profile": UserProfile(name="Alice"),
        "needs": VehicleNeeds(explicit=ExplicitNeeds(brand="BMW", prize="500000")),
        "cars": [{"car_model": "X5"}],
        "reservation": ReservationInfo(
            test_driver="Alice",
            reservation_date="2024-06-01",
            reservation_time="10:00",
            reservation_location="Store",
            reservation_phone_number="123",
        ),
        "expected": Stage.FAREWELL,
    },
    {
        "id": "EC07",
        "description": "Profile advances with only age (partial info)",
        "current": Stage.PROFILE_ANALYSIS,
        "profile": UserProfile(age="25"),
        "needs": VehicleNeeds(),
        "cars": [],
        "reservation": ReservationInfo(),
        "expected": Stage.NEEDS_ANALYSIS,
    },
    {
        "id": "EC08",
        "description": "Needs advances with exactly 2 fields (boundary)",
        "current": Stage.NEEDS_ANALYSIS,
        "profile": UserProfile(),
        "needs": VehicleNeeds(explicit=ExplicitNeeds(prize="100000", brand="Audi")),
        "cars": [],
        "reservation": ReservationInfo(),
        "expected": Stage.CAR_SELECTION,
    },
    {
        "id": "EC09",
        "description": "Reservation stays if date+time but no location",
        "current": Stage.RESERVATION_4S,
        "profile": UserProfile(),
        "needs": VehicleNeeds(),
        "cars": [],
        "reservation": ReservationInfo(
            reservation_date="2024-06-01",
            reservation_time="10:00",
        ),
        "expected": Stage.RESERVATION_4S,
    },
    {
        "id": "EC10",
        "description": "Profile advances with family_size only",
        "current": Stage.PROFILE_ANALYSIS,
        "profile": UserProfile(family_size="4"),
        "needs": VehicleNeeds(),
        "cars": [],
        "reservation": ReservationInfo(),
        "expected": Stage.NEEDS_ANALYSIS,
    },
]


class TestHappyPathTransitions:
    """KPI: Happy-path transition correctness = 100%"""

    @pytest.mark.parametrize("step", HAPPY_PATH_STEPS, ids=[s["id"] for s in HAPPY_PATH_STEPS])
    def test_happy_path_step(self, step):
        result = determine_next_stage(
            step["current"],
            step["profile"],
            step["needs"],
            step["cars"],
            step["reservation"],
        )
        assert result == step["expected"], (
            f"[{step['id']}] {step['description']}: "
            f"expected {step['expected'].value}, got {result.value}"
        )

    def test_full_journey_sequence(self):
        """Run all happy-path steps sequentially and verify 100% correct."""
        passed = 0
        for step in HAPPY_PATH_STEPS:
            result = determine_next_stage(
                step["current"],
                step["profile"],
                step["needs"],
                step["cars"],
                step["reservation"],
            )
            if result == step["expected"]:
                passed += 1
        accuracy = passed / len(HAPPY_PATH_STEPS)
        assert accuracy == 1.0, (
            f"Happy-path accuracy: {accuracy:.0%} ({passed}/{len(HAPPY_PATH_STEPS)})"
        )


class TestEdgeCaseTransitions:
    """KPI: Edge-case transition correctness ≥ 95%"""

    @pytest.mark.parametrize("step", EDGE_CASE_STEPS, ids=[s["id"] for s in EDGE_CASE_STEPS])
    def test_edge_case_step(self, step):
        result = determine_next_stage(
            step["current"],
            step["profile"],
            step["needs"],
            step["cars"],
            step["reservation"],
        )
        assert result == step["expected"], (
            f"[{step['id']}] {step['description']}: "
            f"expected {step['expected'].value}, got {result.value}"
        )

    def test_aggregate_edge_case_accuracy(self):
        """Aggregate edge-case accuracy must be ≥ 95%."""
        passed = 0
        for step in EDGE_CASE_STEPS:
            result = determine_next_stage(
                step["current"],
                step["profile"],
                step["needs"],
                step["cars"],
                step["reservation"],
            )
            if result == step["expected"]:
                passed += 1
        accuracy = passed / len(EDGE_CASE_STEPS)
        assert accuracy >= 0.95, (
            f"Edge-case accuracy: {accuracy:.0%} ({passed}/{len(EDGE_CASE_STEPS)})"
        )
