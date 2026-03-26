"""
Extract test drive reservation information from conversation text.
"""

import json
import logging
from typing import Optional

from llama_index.core.llms import LLM

from app.models.schemas import ReservationInfo

logger = logging.getLogger(__name__)

RESERVATION_EXTRACTION_PROMPT = """You are a reservation extraction assistant for an automotive sales system.
Given the conversation history, extract any test drive reservation details the user has mentioned.

ONLY extract information that is explicitly stated. Do NOT guess or infer.
Leave fields as empty strings if not mentioned.

Fields to extract:
- test_driver: Name of the person who will do the test drive
- reservation_date: Date of the reservation (YYYY-MM-DD format if possible)
- reservation_time: Time of the reservation (HH:MM format if possible)
- reservation_location: Dealership or location for the test drive
- reservation_phone_number: Contact phone number for the reservation
- salesman: Name of the salesperson if mentioned

Current reservation info:
{current_reservation}

Conversation:
{conversation}

Return ONLY a valid JSON object with the extracted fields."""


def extract_reservation(
    llm: LLM,
    conversation: str,
    current_reservation: Optional[ReservationInfo] = None,
) -> ReservationInfo:
    """
    Extract reservation information from conversation using LLM.

    Args:
        llm: The LLM instance to use for extraction.
        conversation: The conversation text to extract from.
        current_reservation: Existing reservation to merge with.

    Returns:
        Updated ReservationInfo with extracted information.
    """
    if current_reservation is None:
        current_reservation = ReservationInfo()

    prompt = RESERVATION_EXTRACTION_PROMPT.format(
        current_reservation=current_reservation.model_dump_json(indent=2),
        conversation=conversation,
    )

    try:
        response = llm.complete(prompt)
        response_text = response.text.strip()

        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0].strip()
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0].strip()

        extracted = json.loads(response_text)

        merged = current_reservation.model_dump()
        for key, value in extracted.items():
            if key in merged and value and str(value).strip():
                merged[key] = str(value).strip()

        return ReservationInfo(**merged)

    except Exception as e:
        logger.warning(f"Reservation extraction failed: {e}")
        return current_reservation
