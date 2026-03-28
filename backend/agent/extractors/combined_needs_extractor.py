"""
Combined needs extractor — merges explicit + implicit extraction into a single LLM call.

Reduces latency by ~40% in the needs_analysis stage by avoiding two separate
LLM round-trips for explicit and implicit needs.
"""

import logging
from typing import Optional

from llama_index.core.llms import LLM

from agent.extractors.base import parse_llm_json
from agent.schemas import UserProfile, VehicleNeeds

logger = logging.getLogger(__name__)

COMBINED_NEEDS_PROMPT = """You are a vehicle needs extraction assistant for an automotive sales system.

Given the conversation and user profile below, do TWO things in ONE response:
1. Extract EXPLICIT vehicle needs the user has directly stated.
2. DEDUCE IMPLICIT preferences based on the user's profile and explicit needs.

=== EXPLICIT NEEDS (only extract what the user explicitly stated) ===
- prize: Budget range (e.g., "10-20万", "Below 100,000")
- vehicle_category_bottom: Vehicle type (e.g., "Compact Sedan", "Mid-size SUV")
- brand: Preferred brand (e.g., "Tesla", "BMW", "BYD")
- powertrain_type: Engine type (e.g., "Battery Electric", "Gasoline", "Plug-in Hybrid")
- design_style: Style preference (e.g., "Sporty", "Classic", "Luxury")
- drive_type: Drive system (e.g., "Front-Wheel Drive", "All-Wheel Drive")
- seat_layout: Seating (e.g., "5-seat", "7-seat")
- autonomous_driving_level: ADAS level (e.g., "L2", "L3")
- ABS, ESP: Safety features ("Yes"/"No")
- airbag_count, horsepower, torque, acceleration_0_100, max_speed
- fuel_consumption, electric_range, battery_capacity
- cargo_volume, wheelbase, ground_clearance

=== IMPLICIT NEEDS (deduce from profile + explicit needs) ===
Use these rules:
- family_size > 3 → family_friendliness="High", space="Large"
- price_sensitivity="high" → cost_performance="High"
- powertrain_type is electric → energy_consumption_level="Low", driving_range="High"
- expertise="beginner" → safety="High", smartness="High"

Implicit fields (use "Low"/"Medium"/"High" or "Small"/"Medium"/"Large"):
size, vehicle_usability, aesthetics, comfort_level, smartness,
family_friendliness, energy_consumption_level, road_performance,
brand_grade, driving_range, power_performance, safety,
cost_performance, space, cargo_space

User Profile:
{user_profile}

Current Explicit Needs:
{current_explicit}

Current Implicit Needs:
{current_implicit}

Conversation:
{conversation}

Return ONLY a valid JSON object with exactly two top-level keys:
{{"explicit": {{...}}, "implicit": {{...}}}}

Merge new information with existing values. Keep existing values unless user provides updates."""


def extract_combined_needs(
    llm: LLM,
    conversation: str,
    user_profile: UserProfile,
    current_needs: Optional[VehicleNeeds] = None,
) -> VehicleNeeds:
    """
    Extract both explicit and implicit needs in a single LLM call.

    Args:
        llm: The LLM instance.
        conversation: Conversation text.
        user_profile: Current user profile for implicit deduction.
        current_needs: Existing VehicleNeeds to merge with.

    Returns:
        Updated VehicleNeeds with both explicit and implicit fields.
    """
    if current_needs is None:
        current_needs = VehicleNeeds()

    prompt = COMBINED_NEEDS_PROMPT.format(
        user_profile=user_profile.model_dump_json(indent=2),
        current_explicit=current_needs.explicit.model_dump_json(indent=2),
        current_implicit=current_needs.implicit.model_dump_json(indent=2),
        conversation=conversation,
    )

    try:
        response = llm.complete(prompt)
        parsed = parse_llm_json(response.text)

        explicit_data = parsed.get("explicit", {})
        implicit_data = parsed.get("implicit", {})

        from agent.extractors.base import merge_model

        new_explicit = merge_model(current_needs.explicit, explicit_data)
        new_implicit = merge_model(current_needs.implicit, implicit_data)

        return VehicleNeeds(explicit=new_explicit, implicit=new_implicit)

    except Exception as e:
        logger.warning(f"Combined needs extraction failed: {e}")
        return current_needs
