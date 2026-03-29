"""
Global information extractor — extracts ALL dimensions in a single LLM call.

Replaces the stage-gated extraction approach. The agent now extracts
profile, needs, and reservation info from EVERY turn, regardless of
current stage. This solves the "user says everything in one message"
problem (scenario E03) and enables cross-stage jumping.
"""

import logging

from llama_index.core.llms import LLM

from agent.extractors.base import merge_model, parse_llm_json
from agent.schemas import (
    ReservationInfo,
    SessionState,
    UserProfile,
)

logger = logging.getLogger(__name__)

GLOBAL_EXTRACTION_PROMPT = """You are an information extraction assistant for an automotive sales system.

Given the conversation below, extract ALL information the user has mentioned,
across ALL categories simultaneously. Only extract what is explicitly stated
or clearly implied. Leave fields as empty strings if not mentioned.

=== CATEGORY 1: USER PROFILE ===
- phone_number, name, title, age, target_driver, expertise
- family_size, price_sensitivity, residence, parking_conditions

=== CATEGORY 2: EXPLICIT VEHICLE NEEDS ===
- prize (budget range), vehicle_category_bottom (vehicle type)
- brand, powertrain_type, design_style, drive_type, seat_layout
- autonomous_driving_level, ABS, ESP, airbag_count
- horsepower, torque, acceleration_0_100, max_speed
- fuel_consumption, electric_range, battery_capacity
- cargo_volume, wheelbase, ground_clearance

=== CATEGORY 3: IMPLICIT VEHICLE NEEDS ===
Deduce from profile + explicit needs using these rules:
- family_size > 3 → family_friendliness="High", space="Large"
- price_sensitivity="high" → cost_performance="High"
- powertrain is electric → energy_consumption_level="Low", driving_range="High"
- expertise="beginner" → safety="High", smartness="High"

Fields (use "Low"/"Medium"/"High" or "Small"/"Medium"/"Large"):
size, vehicle_usability, aesthetics, comfort_level, smartness,
family_friendliness, energy_consumption_level, road_performance,
brand_grade, driving_range, power_performance, safety,
cost_performance, space, cargo_space

=== CATEGORY 4: RESERVATION INFO ===
- test_driver, reservation_date, reservation_time
- reservation_location, reservation_phone_number, salesman

Current known state:
- Profile: {current_profile}
- Explicit Needs: {current_explicit}
- Implicit Needs: {current_implicit}
- Reservation: {current_reservation}

Conversation:
{conversation}

Return ONLY a valid JSON with exactly four top-level keys:
{{"profile": {{...}}, "explicit": {{...}}, "implicit": {{...}}, "reservation": {{...}}}}

Rules:
- Merge new info with existing values. Keep existing unless user provides updates.
- Do NOT fabricate information. Only extract what is stated or clearly implied.
- Leave fields as empty strings if not mentioned."""


def extract_global(
    llm: LLM,
    conversation: str,
    current_state: SessionState,
) -> SessionState:
    """
    Extract all dimensions of information in a single LLM call.

    This replaces the previous stage-gated extraction that only ran
    profile extraction in profile stages, needs in needs stages, etc.
    Now all extractors run every turn, enabling cross-stage jumping.

    Args:
        llm: The LLM instance.
        conversation: Full conversation text.
        current_state: Current session state to merge into.

    Returns:
        Updated SessionState with all extracted information.
    """
    prompt = GLOBAL_EXTRACTION_PROMPT.format(
        current_profile=current_state.profile.model_dump_json(indent=2),
        current_explicit=current_state.needs.explicit.model_dump_json(indent=2),
        current_implicit=current_state.needs.implicit.model_dump_json(indent=2),
        current_reservation=current_state.reservation.model_dump_json(indent=2),
        conversation=conversation,
    )

    try:
        response = llm.complete(prompt)
        parsed = parse_llm_json(response.text)

        # Merge each category
        profile_data = parsed.get("profile", {})
        explicit_data = parsed.get("explicit", {})
        implicit_data = parsed.get("implicit", {})
        reservation_data = parsed.get("reservation", {})

        if profile_data:
            current_state.profile = merge_model(
                current_state.profile, profile_data
            )
        if explicit_data:
            current_state.needs.explicit = merge_model(
                current_state.needs.explicit, explicit_data
            )
        if implicit_data:
            current_state.needs.implicit = merge_model(
                current_state.needs.implicit, implicit_data
            )
        if reservation_data:
            current_state.reservation = merge_model(
                current_state.reservation, reservation_data
            )

        return current_state

    except Exception as e:
        logger.warning(f"Global extraction failed: {e}")
        # Retry once with a simpler fallback
        try:
            response = llm.complete(prompt)
            parsed = parse_llm_json(response.text)
            for key, model_attr, cls in [
                ("profile", "profile", UserProfile),
                ("reservation", "reservation", ReservationInfo),
            ]:
                data = parsed.get(key, {})
                if data:
                    setattr(
                        current_state,
                        model_attr,
                        merge_model(getattr(current_state, model_attr), data),
                    )
            explicit_data = parsed.get("explicit", {})
            implicit_data = parsed.get("implicit", {})
            if explicit_data:
                current_state.needs.explicit = merge_model(
                    current_state.needs.explicit, explicit_data
                )
            if implicit_data:
                current_state.needs.implicit = merge_model(
                    current_state.needs.implicit, implicit_data
                )
            return current_state
        except Exception as e2:
            logger.warning(f"Global extraction retry also failed: {e2}")
            return current_state
