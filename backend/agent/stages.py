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
STAGE_TRANSITIONS: Dict[Stage, Set[Stage]] = {
    Stage.WELCOME: {Stage.PROFILE_ANALYSIS},
    Stage.PROFILE_ANALYSIS: {Stage.NEEDS_ANALYSIS},
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

    Args:
        current_stage: Current conversation stage.
        profile: Current user profile.
        needs: Current vehicle needs.
        matched_cars: List of matched car models.
        reservation: Current reservation info.

    Returns:
        The next Stage (may be the same as current if no transition).
    """
    if current_stage == Stage.WELCOME:
        return Stage.PROFILE_ANALYSIS

    if current_stage == Stage.PROFILE_ANALYSIS:
        if should_advance_to_needs(profile):
            return Stage.NEEDS_ANALYSIS
        return current_stage

    if current_stage == Stage.NEEDS_ANALYSIS:
        if should_advance_to_car_selection(needs):
            return Stage.CAR_SELECTION
        return current_stage

    if current_stage == Stage.CAR_SELECTION:
        if should_advance_to_reservation(matched_cars):
            return Stage.RESERVATION_4S
        return current_stage

    if current_stage == Stage.RESERVATION_4S:
        if should_advance_to_confirmation(reservation):
            return Stage.RESERVATION_CONFIRMATION
        return current_stage

    if current_stage == Stage.RESERVATION_CONFIRMATION:
        if should_advance_to_farewell(reservation):
            return Stage.FAREWELL
        return current_stage

    return current_stage
