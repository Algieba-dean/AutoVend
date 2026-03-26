"""
Extract user profile information from conversation text using LLM.

Uses LlamaIndex structured output with Pydantic models to reliably
extract profile fields from natural language conversation.
"""

import json
import logging
from typing import Optional

from llama_index.core.llms import LLM

from app.models.schemas import UserProfile

logger = logging.getLogger(__name__)

PROFILE_EXTRACTION_PROMPT = """You are an information extraction assistant for an automotive sales system.
Given the conversation history below, extract any user profile information mentioned.

ONLY extract information that is explicitly stated or clearly implied in the conversation.
Do NOT fabricate or guess any information. Leave fields as empty strings if not mentioned.

Fields to extract:
- phone_number: User's phone number
- name: User's name
- title: How to address the user (Mr./Ms./etc.)
- age: User's age or age range
- target_driver: Who will primarily drive the car (self/spouse/child/parent/etc.)
- expertise: User's car knowledge level (expert/intermediate/beginner)
- family_size: Number of family members
- price_sensitivity: Sensitivity to price (high/medium/low)
- residence: City or area of residence
- parking_conditions: Parking situation (garage/street/underground/etc.)

Current known profile:
{current_profile}

Conversation:
{conversation}

Return ONLY a valid JSON object with the extracted fields. Merge new information with existing profile - keep existing values unless the user provides updates."""


def extract_profile(
    llm: LLM,
    conversation: str,
    current_profile: Optional[UserProfile] = None,
) -> UserProfile:
    """
    Extract user profile from conversation using LLM structured output.

    Args:
        llm: The LLM instance to use for extraction.
        conversation: The conversation text to extract from.
        current_profile: Existing profile to merge with. New info overwrites.

    Returns:
        Updated UserProfile with extracted information.
    """
    if current_profile is None:
        current_profile = UserProfile()

    prompt = PROFILE_EXTRACTION_PROMPT.format(
        current_profile=current_profile.model_dump_json(indent=2),
        conversation=conversation,
    )

    try:
        response = llm.complete(prompt)
        response_text = response.text.strip()

        # Try to parse JSON from the response
        # Handle potential markdown code blocks
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0].strip()
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0].strip()

        extracted = json.loads(response_text)

        # Merge: keep existing non-empty values, update with new non-empty values
        merged = current_profile.model_dump()
        for key, value in extracted.items():
            if key in merged and value and str(value).strip():
                merged[key] = str(value).strip()

        return UserProfile(**merged)

    except Exception as e:
        logger.warning(f"Profile extraction failed: {e}")
        return current_profile
