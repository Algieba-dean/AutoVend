"""
Deduce implicit vehicle needs from user profile and explicit needs.

Uses LLM reasoning to infer subjective vehicle attributes (comfort level,
family-friendliness, etc.) based on what's known about the user.
"""

import json
import logging
from typing import Optional

from llama_index.core.llms import LLM

from app.models.schemas import ExplicitNeeds, ImplicitNeeds, UserProfile

logger = logging.getLogger(__name__)

IMPLICIT_DEDUCTION_PROMPT = """You are a vehicle recommendation assistant. Based on the user's profile and explicit vehicle needs, deduce implicit preferences.

Use your automotive expertise to infer these subjective attributes:
- size: Vehicle size preference ("Small", "Medium", "Large")
- vehicle_usability: How versatile ("Small", "Medium", "Large")
- aesthetics: Style importance ("Small", "Medium", "Large")
- comfort_level: Comfort expectation ("Low", "Medium", "High")
- smartness: Tech/smart features importance ("Low", "Medium", "High")
- family_friendliness: Family suitability ("Low", "Medium", "High")
- energy_consumption_level: Fuel efficiency priority ("Low", "Medium", "High")
- road_performance: Off-road/road performance ("Low", "Medium", "High")
- brand_grade: Brand prestige expectation ("Low", "Medium", "High")
- driving_range: Range requirement ("Low", "Medium", "High")
- power_performance: Power importance ("Low", "Medium", "High")
- safety: Safety priority ("Low", "Medium", "High")
- cost_performance: Value-for-money priority ("Low", "Medium", "High")
- space: Interior space need ("Small", "Medium", "Large")
- cargo_space: Cargo space need ("Small", "Medium", "Large")

User Profile:
{user_profile}

Explicit Needs:
{explicit_needs}

Current Implicit Needs:
{current_implicit}

Rules:
1. If family_size > 3 or target_driver involves family → family_friendliness = "High", space = "Large"
2. If price_sensitivity = "high" → cost_performance = "High"
3. If powertrain_type is electric → energy_consumption_level = "Low", driving_range = "High"
4. If expertise = "beginner" → safety = "High", smartness = "High"
5. Only update fields you can reasonably deduce. Leave others unchanged.

Return ONLY a valid JSON object with the deduced fields."""


def deduce_implicit_needs(
    llm: LLM,
    user_profile: UserProfile,
    explicit_needs: ExplicitNeeds,
    current_implicit: Optional[ImplicitNeeds] = None,
) -> ImplicitNeeds:
    """
    Deduce implicit vehicle needs from profile and explicit needs.

    Args:
        llm: The LLM instance to use.
        user_profile: Current user profile.
        explicit_needs: Current explicit vehicle needs.
        current_implicit: Existing implicit needs to update.

    Returns:
        Updated ImplicitNeeds with deduced values.
    """
    if current_implicit is None:
        current_implicit = ImplicitNeeds()

    prompt = IMPLICIT_DEDUCTION_PROMPT.format(
        user_profile=user_profile.model_dump_json(indent=2),
        explicit_needs=explicit_needs.model_dump_json(indent=2),
        current_implicit=current_implicit.model_dump_json(indent=2),
    )

    try:
        response = llm.complete(prompt)
        response_text = response.text.strip()

        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0].strip()
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0].strip()

        deduced = json.loads(response_text)

        merged = current_implicit.model_dump()
        for key, value in deduced.items():
            if key in merged and value and str(value).strip():
                merged[key] = str(value).strip()

        return ImplicitNeeds(**merged)

    except Exception as e:
        logger.warning(f"Implicit needs deduction failed: {e}")
        return current_implicit
