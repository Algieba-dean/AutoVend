"""
Extract user profile information from conversation text using LLM.
"""

from typing import Optional

from llama_index.core.llms import LLM

from agent.extractors.base import extract_with_llm
from agent.schemas import UserProfile

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

    return extract_with_llm(llm, prompt, current_profile)
