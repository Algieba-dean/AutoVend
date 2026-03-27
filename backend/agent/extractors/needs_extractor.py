"""
Extract explicit vehicle needs from conversation text using LLM.
"""

from typing import Optional

from llama_index.core.llms import LLM

from agent.extractors.base import extract_with_llm
from agent.schemas import ExplicitNeeds

NEEDS_EXTRACTION_PROMPT = """You are a vehicle needs extraction assistant for an automotive sales system.
Given the conversation history below, extract any explicit vehicle requirements the user has mentioned.

ONLY extract information that is explicitly stated. Do NOT guess or infer.
Leave fields as empty strings if the user hasn't mentioned them.

Fields to extract:
- prize: Budget range (e.g., "10,000~20,000", "Below 10,000", "Above 100,000")
- vehicle_category_bottom: Vehicle type (e.g., "Compact Sedan", "Mid-size SUV", "Pickup Truck")
- brand: Preferred brand (e.g., "Tesla", "BMW", "BYD")
- powertrain_type: Engine type (e.g., "Battery Electric Vehicle", "Gasoline Engine", "Plug-in Hybrid")
- design_style: Style preference (e.g., "Sporty", "Classic", "Luxury", "Rugged")
- drive_type: Drive system (e.g., "Front-Wheel Drive", "All-Wheel Drive", "Rear-Wheel Drive")
- seat_layout: Seating (e.g., "5-seat", "7-seat", "2-seat")
- autonomous_driving_level: ADAS level (e.g., "L2", "L3", "L4")
- ABS, ESP: Safety features ("Yes"/"No")
- airbag_count: Number of airbags
- horsepower, torque, acceleration_0_100, max_speed: Performance specs
- fuel_consumption, electric_range, battery_capacity: Efficiency specs
- cargo_volume, wheelbase, ground_clearance: Dimension specs

Current known needs:
{current_needs}

Conversation:
{conversation}

Return ONLY a valid JSON object with the extracted fields. Merge new information with existing needs."""


def extract_explicit_needs(
    llm: LLM,
    conversation: str,
    current_needs: Optional[ExplicitNeeds] = None,
) -> ExplicitNeeds:
    """
    Extract explicit vehicle needs from conversation using LLM.

    Args:
        llm: The LLM instance to use for extraction.
        conversation: The conversation text to extract from.
        current_needs: Existing needs to merge with.

    Returns:
        Updated ExplicitNeeds with extracted information.
    """
    if current_needs is None:
        current_needs = ExplicitNeeds()

    prompt = NEEDS_EXTRACTION_PROMPT.format(
        current_needs=current_needs.model_dump_json(indent=2),
        conversation=conversation,
    )

    return extract_with_llm(llm, prompt, current_needs)
