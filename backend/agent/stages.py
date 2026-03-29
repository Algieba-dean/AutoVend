"""
Stage definitions and transition rules for the conversation workflow.

Defines valid stage transitions and provides logic for determining
when a stage transition should occur based on collected information.
"""

import logging
from typing import Dict, List, Set

from agent.schemas import (
    ReservationInfo,
    Stage,
    UserProfile,
    VehicleNeeds,
)

logger = logging.getLogger(__name__)

# Valid stage transitions: current_stage → set of allowed next stages
# Now includes multi-hop transitions for cross-stage jumping
STAGE_TRANSITIONS: Dict[Stage, Set[Stage]] = {
    Stage.WELCOME: {
        Stage.PROFILE_ANALYSIS, Stage.NEEDS_ANALYSIS,
        Stage.CAR_SELECTION,
    },
    Stage.PROFILE_ANALYSIS: {
        Stage.NEEDS_ANALYSIS, Stage.CAR_SELECTION,
    },
    Stage.NEEDS_ANALYSIS: {Stage.CAR_SELECTION},
    Stage.CAR_SELECTION: {Stage.RESERVATION_4S, Stage.NEEDS_ANALYSIS},
    Stage.RESERVATION_4S: {Stage.RESERVATION_CONFIRMATION},
    Stage.RESERVATION_CONFIRMATION: {Stage.FAREWELL, Stage.RESERVATION_4S},
    Stage.FAREWELL: set(),
}

# Ordered list of all stages for reference
STAGE_ORDER: List[Stage] = [
    Stage.WELCOME,
    Stage.PROFILE_ANALYSIS,
    Stage.NEEDS_ANALYSIS,
    Stage.CAR_SELECTION,
    Stage.RESERVATION_4S,
    Stage.RESERVATION_CONFIRMATION,
    Stage.FAREWELL,
]


def can_transition(current: Stage, target: Stage) -> bool:
    """Check if a transition from current to target stage is valid."""
    return target in STAGE_TRANSITIONS.get(current, set())


def should_advance_to_needs(profile: UserProfile) -> bool:
    """
    Check if enough profile info is collected to move to needs analysis.
    Requires at least name or some identifying info.
    """
    return any(
        [
            profile.name,
            profile.age,
            profile.target_driver,
            profile.family_size,
        ]
    )


def should_advance_to_car_selection(needs: VehicleNeeds) -> bool:
    """
    Check if enough explicit needs are collected to recommend cars.
    Requires at least 2 key fields filled.
    """
    explicit = needs.explicit
    filled_count = sum(
        1
        for v in [
            explicit.prize,
            explicit.brand,
            explicit.powertrain_type,
            explicit.vehicle_category_bottom,
            explicit.design_style,
            explicit.seat_layout,
        ]
        if v
    )
    return filled_count >= 2


def should_advance_to_reservation(matched_cars: list) -> bool:
    """
    Check if car selection is confirmed and we can proceed to reservation.
    Requires at least one matched car.
    """
    return len(matched_cars) > 0


def should_advance_to_confirmation(reservation: ReservationInfo) -> bool:
    """
    Check if enough reservation info is collected for confirmation.
    Requires at least date, time, and location.
    """
    return all(
        [
            reservation.reservation_date,
            reservation.reservation_time,
            reservation.reservation_location,
        ]
    )


def should_advance_to_farewell(reservation: ReservationInfo) -> bool:
    """
    Check if reservation is fully confirmed and we can say goodbye.
    """
    return all(
        [
            reservation.test_driver,
            reservation.reservation_date,
            reservation.reservation_time,
            reservation.reservation_location,
            reservation.reservation_phone_number,
        ]
    )


def determine_next_stage(
    current_stage: Stage,
    profile: UserProfile,
    needs: VehicleNeeds,
    matched_cars: list,
    reservation: ReservationInfo,
) -> Stage:
    """
    Determine the next conversation stage based on current state.

    Supports cross-stage jumping: if the user provides profile AND needs
    in a single message, the agent can skip directly from WELCOME to
    CAR_SELECTION (if enough info is present). This scans forward through
    the stage order and returns the furthest reachable stage.

    Args:
        current_stage: Current conversation stage.
        profile: Current user profile.
        needs: Current vehicle needs.
        matched_cars: List of matched car models.
        reservation: Current reservation info.

    Returns:
        The next Stage (may be the same as current if no transition).
    """
    # FAREWELL is terminal
    if current_stage == Stage.FAREWELL:
        return current_stage

    # WELCOME always advances at minimum to PROFILE_ANALYSIS
    if current_stage == Stage.WELCOME:
        candidate = Stage.PROFILE_ANALYSIS
    else:
        candidate = current_stage

    # Scan forward: try to advance as far as the data supports
    # Each check tests whether we can PASS THROUGH a stage
    current_idx = STAGE_ORDER.index(candidate)

    # Can we reach or pass NEEDS_ANALYSIS?
    if current_idx <= STAGE_ORDER.index(Stage.PROFILE_ANALYSIS):
        if should_advance_to_needs(profile):
            candidate = Stage.NEEDS_ANALYSIS
        else:
            return candidate

    # Can we reach or pass CAR_SELECTION?
    if candidate == Stage.NEEDS_ANALYSIS:
        if should_advance_to_car_selection(needs):
            candidate = Stage.CAR_SELECTION
        else:
            return candidate

    # Can we reach RESERVATION_4S?
    if candidate == Stage.CAR_SELECTION:
        if should_advance_to_reservation(matched_cars):
            candidate = Stage.RESERVATION_4S
        else:
            return candidate

    # Can we reach RESERVATION_CONFIRMATION?
    if candidate == Stage.RESERVATION_4S:
        if should_advance_to_confirmation(reservation):
            candidate = Stage.RESERVATION_CONFIRMATION
        else:
            return candidate

    # Can we reach FAREWELL?
    if candidate == Stage.RESERVATION_CONFIRMATION:
        if should_advance_to_farewell(reservation):
            candidate = Stage.FAREWELL
        else:
            return candidate

    return candidate
