"""
Response generation strategies for each conversation stage.

Each stage has a tailored prompt template that combines context
(profile, needs, matched cars, etc.) to generate appropriate responses.
"""

import logging
from typing import Any, Dict, List

from llama_index.core.llms import LLM

from agent.schemas import (
    ReservationInfo,
    Stage,
    UserProfile,
    VehicleNeeds,
)

logger = logging.getLogger(__name__)

STAGE_PROMPTS: Dict[str, str] = {
    Stage.WELCOME: """You are AutoVend, a friendly and professional automotive sales assistant.
The customer just started a conversation. Greet them warmly, introduce yourself briefly,
and ask about their basic information (name, who will be driving, etc.) to start building their profile.
Keep the greeting concise and natural.

Conversation so far:
{conversation_history}

Respond naturally in the same language the user uses.""",
    Stage.PROFILE_ANALYSIS: """You are AutoVend, a professional automotive sales assistant.
You are gathering the customer's profile information through natural conversation.

Current profile:
{profile}

Information still needed: {missing_profile_fields}

Conversation so far:
{conversation_history}

Continue the conversation naturally, asking about missing profile information.
Don't ask all questions at once - be conversational. If enough info is gathered,
smoothly transition to asking about their car preferences.
Respond in the same language the user uses.""",
    Stage.NEEDS_ANALYSIS: """You are AutoVend, a professional automotive sales assistant.
You are helping the customer articulate their vehicle needs.

Customer profile:
{profile}

Current explicit needs:
{explicit_needs}

Current implicit needs:
{implicit_needs}

Key needs still to explore: {missing_needs_fields}

Conversation so far:
{conversation_history}

Help the customer think through what they need in a vehicle. Ask about:
- Budget range, preferred brands, vehicle type
- Powertrain preference (EV/hybrid/gasoline)
- Key features they care about (safety, comfort, technology)
Be conversational and don't overwhelm them. Respond in the same language the user uses.""",
    Stage.CAR_SELECTION: """You are AutoVend, a professional automotive sales assistant.
Based on the customer's needs, present vehicle recommendations.

Customer profile:
{profile}

Explicit needs:
{explicit_needs}

Implicit needs:
{implicit_needs}

Matched vehicles:
{matched_cars}

Conversation so far:
{conversation_history}

Present the matched vehicles clearly, highlighting why each matches their needs.
Compare key differences between options. Ask if they'd like to test drive any.
Respond in the same language the user uses.""",
    Stage.RESERVATION_4S: """You are AutoVend, a professional automotive sales assistant.
The customer wants to schedule a test drive. Collect reservation details.

Customer profile:
{profile}

Selected vehicle(s):
{matched_cars}

Current reservation info:
{reservation}

Missing reservation fields: {missing_reservation_fields}

Conversation so far:
{conversation_history}

Help the customer schedule their test drive by collecting:
- Preferred date and time
- Preferred dealership location
- Contact phone number
- Who will be test driving
Be helpful and suggest options when appropriate. Respond in the same language the user uses.""",
    Stage.RESERVATION_CONFIRMATION: """You are AutoVend, a professional automotive sales assistant.
Confirm the test drive reservation details with the customer.

Reservation details:
- Driver: {reservation_driver}
- Date: {reservation_date}
- Time: {reservation_time}
- Location: {reservation_location}
- Phone: {reservation_phone}

Vehicle: {matched_cars}

Conversation so far:
{conversation_history}

Summarize the reservation details and ask the customer to confirm.
If they want to change anything, help them update the details.
Respond in the same language the user uses.""",
    Stage.FAREWELL: """You are AutoVend, a professional automotive sales assistant.
The customer's test drive has been booked. Wrap up the conversation.

Reservation confirmed for:
- Vehicle: {matched_cars}
- Date: {reservation_date} at {reservation_time}
- Location: {reservation_location}

Conversation so far:
{conversation_history}

Thank the customer, confirm next steps, and say goodbye warmly.
Respond in the same language the user uses.""",
}


def _get_missing_profile_fields(profile: UserProfile) -> str:
    """Get a comma-separated list of empty profile fields."""
    fields = profile.model_dump()
    missing = [k for k, v in fields.items() if not v]
    return ", ".join(missing) if missing else "None (profile complete)"


def _get_missing_needs_fields(needs: VehicleNeeds) -> str:
    """Get key unfilled explicit needs fields."""
    explicit = needs.explicit.model_dump()
    key_fields = ["prize", "brand", "powertrain_type", "vehicle_category_bottom", "design_style"]
    missing = [k for k in key_fields if not explicit.get(k)]
    return ", ".join(missing) if missing else "None (key needs identified)"


def _get_missing_reservation_fields(reservation: ReservationInfo) -> str:
    """Get unfilled reservation fields."""
    fields = reservation.model_dump()
    missing = [k for k, v in fields.items() if not v]
    return ", ".join(missing) if missing else "None (reservation complete)"


def _format_matched_cars(matched_cars: List[Dict[str, Any]]) -> str:
    """Format matched cars for prompt injection."""
    if not matched_cars:
        return "No vehicles matched yet."
    lines = []
    for i, car in enumerate(matched_cars, 1):
        name = car.get("car_model", "Unknown")
        score = car.get("score", "N/A")
        snippet = car.get("text_snippet", "")[:200]
        lines.append(f"{i}. {name} (relevance: {score})\n   {snippet}")
    return "\n".join(lines)


def generate_response(
    llm: LLM,
    stage: Stage,
    conversation_history: str,
    profile: UserProfile,
    needs: VehicleNeeds,
    matched_cars: List[Dict[str, Any]],
    reservation: ReservationInfo,
) -> str:
    """
    Generate a response for the current conversation stage.

    Args:
        llm: The LLM instance.
        stage: Current conversation stage.
        conversation_history: Formatted conversation text.
        profile: Current user profile.
        needs: Current vehicle needs.
        matched_cars: List of matched vehicle dicts.
        reservation: Current reservation info.

    Returns:
        Generated response text.
    """
    prompt_template = STAGE_PROMPTS.get(stage, STAGE_PROMPTS[Stage.WELCOME])

    prompt = prompt_template.format(
        conversation_history=conversation_history,
        profile=profile.model_dump_json(indent=2),
        explicit_needs=needs.explicit.model_dump_json(indent=2),
        implicit_needs=needs.implicit.model_dump_json(indent=2),
        matched_cars=_format_matched_cars(matched_cars),
        reservation=reservation.model_dump_json(indent=2),
        missing_profile_fields=_get_missing_profile_fields(profile),
        missing_needs_fields=_get_missing_needs_fields(needs),
        missing_reservation_fields=_get_missing_reservation_fields(reservation),
        reservation_driver=reservation.test_driver,
        reservation_date=reservation.reservation_date,
        reservation_time=reservation.reservation_time,
        reservation_location=reservation.reservation_location,
        reservation_phone=reservation.reservation_phone_number,
    )

    try:
        response = llm.complete(prompt)
        return response.text.strip()
    except Exception as e:
        logger.error(f"Response generation failed: {e}")
        return (
            "I apologize, but I'm having trouble generating a response. Could you please try again?"
        )
