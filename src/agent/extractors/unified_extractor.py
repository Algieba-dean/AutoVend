"""
Unified Slot Extractor for Two-Stage / Single-Flight Pipeline (src/agent/extractors/unified_extractor.py).

Extracts customer profile, vehicle requirements, test-drive booking, and retracted constraints
in ONE single LLM call via LangChain `with_structured_output(UpdateSessionSlotsTool)`.
"""

import logging
from typing import Any, Tuple

from langchain_core.messages import HumanMessage, SystemMessage

from src.agent.schemas import SessionState
from src.agent.unified_schema import UpdateSessionSlotsTool, apply_slot_updates
from src.llm.langchain_adapter import ensure_chat_model

logger = logging.getLogger(__name__)

UNIFIED_SYSTEM_INSTRUCTION = """You are an intelligent automotive sales slot extraction engine.
Analyze the conversation transcript and extract any updated customer profile, vehicle preferences, test-drive reservations, or explicit retractions.

Output a single JSON object with the following schema:
{
  "customer_name": "Customer name or None",
  "age": null or integer (18-100),
  "city": "Residence city or None",
  "phone_number": "Phone number or None",
  "budget_min_wan": null or float (e.g. 20.0),
  "budget_max_wan": null or float (e.g. 30.0),
  "preferred_powertrain": "纯电 / 插混 / 增程 / 燃油 or None",
  "seat_count": null or integer (2-9),
  "brand_preference": "Brand or None",
  "vehicle_category": "轿车 / SUV / MPV / 猎装 / 轿跑 or None",
  "reservation_date": "Standard YYYY-MM-DD or relative like '明天' or None",
  "reservation_time_slot": "上午 / 下午 / 晚上 / 14:00 or None",
  "preferred_4s_store": "Dealership store name or None",
  "retracted_fields": ["list", "of", "fields", "customer", "cancelled", "e.g.", "budget", "suv"]
}

Rules:
1. ONLY extract explicitly mentioned or clearly confirmed attributes.
2. If the user retracts or rejects a previous constraint (e.g. "不要SUV了", "预算改一下"), add it to "retracted_fields".
3. Return ONLY valid JSON, no markdown formatting or extra text."""


def extract_unified_slots(
    llm: Any,
    conversation_text: str,
    state: SessionState,
) -> Tuple[SessionState, UpdateSessionSlotsTool]:
    """
    Extract profile, needs, reservations, and retractions in a single LLM invocation
    using LangChain `chat_model.with_structured_output(UpdateSessionSlotsTool)`.
    """
    chat_model = ensure_chat_model(llm)
    structured_llm = chat_model.with_structured_output(UpdateSessionSlotsTool)
    messages = [
        SystemMessage(content=UNIFIED_SYSTEM_INSTRUCTION),
        HumanMessage(content=f"Conversation transcript:\n{conversation_text}\n\nJSON:"),
    ]
    try:
        tool_data: UpdateSessionSlotsTool = structured_llm.invoke(messages)
        updated_state = apply_slot_updates(state, tool_data)
        return updated_state, tool_data
    except Exception as exc:
        logger.warning(f"Unified slot extraction failed, keeping previous state: {exc}")
        return state, UpdateSessionSlotsTool()
