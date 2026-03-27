"""Re-export from agent.stages for backward compatibility."""

from agent.stages import (  # noqa: F401
    STAGE_ORDER,
    STAGE_TRANSITIONS,
    can_transition,
    determine_next_stage,
    should_advance_to_car_selection,
    should_advance_to_confirmation,
    should_advance_to_farewell,
    should_advance_to_needs,
    should_advance_to_reservation,
)
