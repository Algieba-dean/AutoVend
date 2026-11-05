"""
Response generation strategies for each conversation stage.

Each stage has a tailored prompt template structured with a 100% static
system instruction prefix (enabling LLM provider KV prefix caching),
followed by dynamic session state and conversation history at the tail.
"""

import logging
import re
from typing import Any, Dict, List, Optional

from llama_index.core.llms import LLM

from src.agent.schemas import (
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
Respond naturally in the same language the user uses.

Conversation so far:
{conversation_history}""",
    Stage.PROFILE_ANALYSIS: """You are AutoVend, a professional automotive sales assistant.
You are gathering the customer's profile information through natural conversation.
Continue the conversation naturally, asking about missing profile information.
Don't ask all questions at once - be conversational. If enough info is gathered,
smoothly transition to asking about their car preferences.
Respond in the same language the user uses.

Current profile:
{profile}

Information still needed: {missing_profile_fields}

Conversation so far:
{conversation_history}""",
    Stage.NEEDS_ANALYSIS: """You are AutoVend, an expert automotive sales consultant using the SPIN Selling methodology (Situation, Problem, Implication, Need-payoff).
You are helping the customer articulate and discover their true vehicle needs through consultative dialogue.

SPIN Sales Guidance:
1. Situation (现状询问): Ask gentle questions about current driving habits, daily commute, family usage, and charging/fueling convenience.
2. Problem (痛点挖掘): Help the customer uncover pain points with their current car or pain points in their driving scenarios (e.g. cramped rear seat, high fuel bills, lack of smart driving).
3. Implication (影响放大): Empathetically guide them to realize how these pain points affect family travel comfort or safety.
4. Need-payoff (需求解药): Highlight how specific car capabilities (e.g. 800V fast charge, 6-seat layout, NVH acoustic glass) solve those exact problems.

Consumer Truth & Anti-Marketing Fluff Guidance (用户立场·去魅与真实透明准则):
- 坚决站在用户利益立场，抽丝剥茧剥离硬宣传与噱头（如说明混动加92号油是行业标配非独创，全栈自研依托Tier-1公版硬件）。
- 客观告知CLTC标称与冬季/高速真实续航的物理差距、峰值充电与平均曲线差异。
- 用严密结构力学解答安全疑虑（如玻纤踏板碰撞溃缩防骨折、One-Box机械液压备份）。

Be conversational, empathetic, and professional. Don't ask all questions at once. Respond in the same language the user uses.

Customer profile:
{profile}

Current explicit needs:
{explicit_needs}

Current implicit needs:
{implicit_needs}

Key needs still to explore: {missing_needs_fields}

Conversation so far:
{conversation_history}""",
    Stage.CAR_SELECTION: """You are AutoVend, a top-tier automotive sales consultant.
Based on the customer's needs and profile, present matched vehicle recommendations with compelling value propositions.

Sales Pitching & Recommendation Guidance:
- Present matched vehicles with structured, high-value highlights matching the customer's specific profile and needs.
- Highlight 2-3 standout features per vehicle (e.g., safety ratings, spatial comfort, smart cockpit, total cost of ownership).
- Perform clear side-by-side trade-off comparisons so the customer can decide easily.
- Consumer Truth & Anti-Fluff Directive: Be unvarnished and honest about real-world test results, failure rates, battery thermal safety standards (GB 38031), depreciation valuation, and transparent drive-away price.
- STRICT CONTEXT COMPLIANCE (忠诚度与零幻觉准则): You MUST quote parameters (price, range, seating, horsepower) ONLY from the provided matched_cars metadata and text_snippet. DO NOT invent, extrapolate, or estimate any specification not present in matched_cars context.
- Proactively invite them to experience the car via a 4S dealership test drive.
- Respond in the same language the user uses.

Customer profile:
{profile}

Explicit needs:
{explicit_needs}

Implicit needs:
{implicit_needs}

Matched vehicles:
{matched_cars}

Conversation so far:
{conversation_history}""",
    Stage.RESERVATION_4S: """You are AutoVend, a professional automotive sales assistant.
The customer wants to schedule a test drive. Help the customer schedule their test drive by collecting:
- Preferred date and time
- Preferred dealership location
- Contact phone number
- Who will be test driving
Be helpful and suggest options when appropriate. Respond in the same language the user uses.

Customer profile:
{profile}

Selected vehicle(s):
{matched_cars}

Current reservation info:
{reservation}

Missing reservation fields: {missing_reservation_fields}

Conversation so far:
{conversation_history}""",
    Stage.RESERVATION_CONFIRMATION: """You are AutoVend, a professional automotive sales assistant.
Confirm the test drive reservation details with the customer.
Summarize the reservation details and ask the customer to confirm.
If they want to change anything, help them update the details.
Respond in the same language the user uses.

Reservation details:
- Driver: {reservation_driver}
- Date: {reservation_date}
- Time: {reservation_time}
- Location: {reservation_location}
- Phone: {reservation_phone}

Vehicle: {matched_cars}

Conversation so far:
{conversation_history}""",
    Stage.FAREWELL: """You are AutoVend, a professional automotive sales assistant.
The customer's test drive has been booked. Wrap up the conversation.
Thank the customer, confirm next steps, and say goodbye warmly.
Respond in the same language the user uses.

Reservation confirmed for:
- Vehicle: {matched_cars}
- Date: {reservation_date} at {reservation_time}
- Location: {reservation_location}

Conversation so far:
{conversation_history}""",
}


def _get_missing_profile_fields(profile: UserProfile) -> str:
    """Get a comma-separated list of empty profile fields."""
    fields = profile.model_dump()
    missing = [k for k, v in fields.items() if not v]
    return ", ".join(missing) if missing else "None (profile complete)"


def _get_missing_needs_fields(needs: VehicleNeeds) -> str:
    """Get key unfilled explicit needs fields."""
    explicit = needs.explicit.model_dump()
    key_fields = ["price", "brand", "powertrain_type", "vehicle_category_bottom", "design_style"]
    missing = [k for k in key_fields if not explicit.get(k)]
    return ", ".join(missing) if missing else "None (key needs identified)"


def _get_missing_reservation_fields(reservation: ReservationInfo) -> str:
    """Get unfilled reservation fields."""
    fields = reservation.model_dump()
    missing = [k for k, v in fields.items() if not v]
    return ", ".join(missing) if missing else "None (reservation complete)"


def _format_matched_cars(matched_cars: List[Dict[str, Any]]) -> str:
    """Format matched cars for prompt injection, skipping redundant compression if already compressed."""
    if not matched_cars:
        return "No vehicles matched yet."
    from src.core.compression import ContextCompressor

    lines = []
    for i, car in enumerate(matched_cars, 1):
        name = car.get("car_model", "Unknown")
        score = car.get("score", "N/A")
        raw_snippet = car.get("text_snippet", "")
        if car.get("compression_meta"):
            snippet = raw_snippet[:220]
        else:
            compressed = ContextCompressor.compress_snippet(raw_snippet, max_length=220)
            snippet = compressed.compressed_text or raw_snippet[:200]
        lines.append(f"{i}. {name} (relevance: {score})\n   {snippet}")
    return "\n".join(lines)


def _build_stage_prompt(
    stage: Stage,
    conversation_history: str,
    profile: UserProfile,
    needs: VehicleNeeds,
    matched_cars: List[Dict[str, Any]],
    reservation: ReservationInfo,
    system_notes: Optional[List[str]] = None,
) -> str:
    """Assemble the complete stage prompt with boundary directive, battlecards, and system notes."""
    prompt_template = STAGE_PROMPTS.get(stage, STAGE_PROMPTS[Stage.WELCOME])

    format_kwargs = {
        "conversation_history": conversation_history,
        "profile": profile.model_dump_json(indent=2),
        "missing_profile_fields": _get_missing_profile_fields(profile),
        "explicit_needs": needs.explicit.model_dump_json(indent=2),
        "implicit_needs": needs.implicit.model_dump_json(indent=2),
        "missing_needs_fields": _get_missing_needs_fields(needs),
        "matched_cars": _format_matched_cars(matched_cars),
        "reservation": reservation.model_dump_json(indent=2),
        "missing_reservation_fields": _get_missing_reservation_fields(reservation),
        "reservation_driver": reservation.test_driver,
        "reservation_date": reservation.reservation_date,
        "reservation_time": reservation.reservation_time,
        "reservation_location": reservation.reservation_location,
        "reservation_phone": reservation.reservation_phone_number,
    }

    prompt = prompt_template.format(**format_kwargs)

    from src.agent.battlecards import match_battlecards
    from src.privacy.prompt_sanitizer import PromptSanitizer

    active_notes = list(system_notes or [])

    _, _, boundary_directive = PromptSanitizer.wrap_context_boundaries(
        conversation_history, format_kwargs.get("matched_cars", "")
    )
    if boundary_directive not in active_notes:
        active_notes.append(boundary_directive)

    battlecards = match_battlecards(conversation_history)
    for card in battlecards:
        card_note = card.to_system_note()
        if card_note not in active_notes:
            active_notes.append(card_note)

    if active_notes:
        prompt = prompt + "\n\n本轮系统指令与近期状态变化：\n" + "\n".join(active_notes)

    return prompt


def generate_response(
    llm: LLM,
    stage: Stage,
    conversation_history: str,
    profile: UserProfile,
    needs: VehicleNeeds,
    matched_cars: List[Dict[str, Any]],
    reservation: ReservationInfo,
    system_notes: Optional[List[str]] = None,
) -> str:
    """
    Generate a response for the current conversation stage.
    """
    prompt = _build_stage_prompt(
        stage=stage,
        conversation_history=conversation_history,
        profile=profile,
        needs=needs,
        matched_cars=matched_cars,
        reservation=reservation,
        system_notes=system_notes,
    )

    try:
        response = llm.complete(prompt)
        text = response.text.strip()
        return redact_output_pii(text)
    except Exception as e:
        logger.error(f"Response generation failed: {e}")
        return (
            "I apologize, but I'm having trouble generating a response. Could you please try again?"
        )


def generate_response_stream(
    llm: LLM,
    stage: Stage,
    conversation_history: str,
    profile: UserProfile,
    needs: VehicleNeeds,
    matched_cars: List[Dict[str, Any]],
    reservation: ReservationInfo,
    system_notes: Optional[List[str]] = None,
):
    """
    Stream response token deltas from LLM.
    Yields string deltas token by token.
    """
    prompt = _build_stage_prompt(
        stage=stage,
        conversation_history=conversation_history,
        profile=profile,
        needs=needs,
        matched_cars=matched_cars,
        reservation=reservation,
        system_notes=system_notes,
    )

    try:
        response_gen = llm.stream_complete(prompt)
        for response_chunk in response_gen:
            delta = getattr(response_chunk, "delta", None)
            if delta is None and hasattr(response_chunk, "text"):
                delta = response_chunk.text
            if delta:
                yield delta
    except Exception as e:
        logger.error(f"Streaming response generation failed: {e}")
        yield "I apologize, but I'm having trouble generating a response."


def redact_output_pii(text: str) -> str:
    """
    Fallback secondary PII redaction on output response before returning to client.
    Redacts standalone 11-digit mobile numbers (e.g. 13812345678 -> 138****5678).
    """
    if not text:
        return text

    def mask_mobile(m):
        phone = m.group(0)
        return f"{phone[:3]}****{phone[7:]}"

    return re.sub(r"\b(1[3-9]\d)\d{4}(\d{4})\b", mask_mobile, text)
