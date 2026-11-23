"""
LangChain LCEL chains for AutoVend response generation (sync & async streaming).

P2 Enterprise Harness:
- 100% static SystemMessage prefix per stage for LLM KV prefix caching;
  dynamic session state, matched_cars, and system_notes are placed at the tail.
- Micro-compact: collapses oversized historical ToolMessages and summarizes
  overflowing dialogue turns instead of hard-truncating `messages[-20:]`.
"""

import logging
import re
from typing import Any, AsyncGenerator, Dict, List, Optional, Sequence

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, ToolMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from src.agent.response_generator import (
    _format_matched_cars,
    _get_missing_needs_fields,
    _get_missing_profile_fields,
    _get_missing_reservation_fields,
)
from src.agent.schemas import (
    PreferenceModel,
    ReservationInfo,
    Stage,
    UserProfile,
    VehicleNeeds,
)
from src.agent.think_scrubber import scrub_think_blocks

logger = logging.getLogger(__name__)

# 100% Static System Prefix (byte-identical across turns -> maximizes KV prefix cache hit rate)
STATIC_SYSTEM_PREFIX = (
    "You are AutoVend, a top-tier, empathetic, and transparent automotive sales consultant.\n"
    "Core Principles:\n"
    "1. Consumer Truth & Anti-Fluff: Be unvarnished and honest about real-world range, charging curves, "
    "safety standards (GB 38031), depreciation, and transparent drive-away price.\n"
    "2. Zero Hallucination: Quote vehicle parameters (price, range, seating, horsepower) ONLY from "
    "the provided matched_cars context and verified tool outputs. Never invent specs.\n"
    "3. Language & Tone: Respond naturally in the same language the customer uses. Keep replies concise and helpful."
)

STATIC_STAGE_GUIDANCE: Dict[Stage, str] = {
    Stage.WELCOME: (
        "Current Stage: WELCOME.\n"
        "Greet the customer warmly, introduce yourself briefly, and ask for basic info (name, who will drive)."
    ),
    Stage.PROFILE_ANALYSIS: (
        "Current Stage: PROFILE_ANALYSIS.\n"
        "Gather missing customer profile information conversationally without asking all questions at once."
    ),
    Stage.NEEDS_ANALYSIS: (
        "Current Stage: NEEDS_ANALYSIS (SPIN Selling).\n"
        "Use Situation, Problem, Implication, Need-payoff to uncover true needs (commute, family, charging)."
    ),
    Stage.CAR_SELECTION: (
        "Current Stage: CAR_SELECTION.\n"
        "Present matched vehicles with 2-3 standout features, clear trade-off comparisons, and invite a 4S test drive."
    ),
    Stage.RESERVATION_4S: (
        "Current Stage: RESERVATION_4S.\n"
        "Help schedule a 4S test drive by collecting date, time, dealership location, driver name, and phone number."
    ),
    Stage.RESERVATION_CONFIRMATION: (
        "Current Stage: RESERVATION_CONFIRMATION.\n"
        "Summarize all reservation details clearly and ask the customer to confirm or request changes."
    ),
    Stage.FAREWELL: (
        "Current Stage: FAREWELL.\n"
        "Confirm the test drive booking, thank the customer, outline next steps, and say goodbye warmly."
    ),
}


def get_static_system_instruction(stage: Stage) -> str:
    """Return the 100% static SystemMessage instruction for `stage` (KV-cache safe)."""
    guidance = STATIC_STAGE_GUIDANCE.get(stage, STATIC_STAGE_GUIDANCE[Stage.WELCOME])
    return f"{STATIC_SYSTEM_PREFIX}\n\n{guidance}"


def micro_compact_messages(
    messages: Sequence[BaseMessage],
    keep_recent_tools: int = 2,
    max_tool_chars: int = 300,
    max_history_messages: int = 16,
) -> List[BaseMessage]:
    """
    Micro-compact conversation history:
    1. Collapse older ToolMessages (beyond the most recent `keep_recent_tools`)
       whose content exceeds `max_tool_chars` into compact stubs.
    2. If non-tool dialogue turns exceed `max_history_messages`, summarize older
       turns into a compact archive message instead of dropping them blindly.
    """
    msg_list = list(messages)
    if not msg_list:
        return []

    # Step 1: Collapse old oversized ToolMessages
    tool_indices = [i for i, m in enumerate(msg_list) if isinstance(m, ToolMessage)]
    keep_tool_set = set(tool_indices[-keep_recent_tools:]) if keep_recent_tools > 0 else set()

    compacted: List[BaseMessage] = []
    for idx, msg in enumerate(msg_list):
        if isinstance(msg, ToolMessage) and idx not in keep_tool_set:
            content_str = msg.content if isinstance(msg.content, str) else str(msg.content)
            if len(content_str) > max_tool_chars:
                tool_name = getattr(msg, "name", None) or "tool"
                stub = f"[ToolOutput compacted: {tool_name}, {len(content_str)} chars]"
                compacted.append(
                    ToolMessage(
                        content=stub,
                        tool_call_id=msg.tool_call_id,
                        name=getattr(msg, "name", None),
                    )
                )
                continue
        compacted.append(msg)

    # Step 2: Summarize overflowing older dialogue turns
    if len(compacted) > max_history_messages:
        split_at = len(compacted) - max_history_messages
        older = compacted[:split_at]
        recent = compacted[split_at:]
        # Never leave an orphaned ToolMessage at the head of `recent`
        while recent and isinstance(recent[0], ToolMessage):
            older.append(recent.pop(0))
        summary_lines: List[str] = []
        for m in older:
            if isinstance(m, ToolMessage):
                continue
            if isinstance(m, AIMessage) and getattr(m, "tool_calls", None) and not m.content:
                continue
            role = "客户" if isinstance(m, HumanMessage) else "顾问"
            text = (m.content if isinstance(m.content, str) else str(m.content)).strip()
            if text:
                summary_lines.append(f"- {role}: {text[:80]}{'...' if len(text) > 80 else ''}")
        if summary_lines:
            archive_msg = HumanMessage(
                content="[历史对话压缩归档]\n" + "\n".join(summary_lines[-8:])
            )
            return [archive_msg, *recent]
        return recent

    return compacted


def _build_dynamic_context_block(
    stage: Stage,
    conversation_history: str,
    profile: UserProfile,
    needs: VehicleNeeds,
    matched_cars: List[Dict[str, Any]],
    reservation: ReservationInfo,
    system_notes: Optional[List[str]] = None,
    preferences: Optional[PreferenceModel] = None,
    pending_confirmation: Optional[Dict[str, Any]] = None,
) -> str:
    """Build dynamic per-turn context block placed at the tail (after static SystemMessage & history)."""
    from src.agent.battlecards import match_battlecards
    from src.agent.preference_model import PreferenceEngine
    from src.privacy.prompt_sanitizer import PromptSanitizer

    sanitized_cars, _ = PromptSanitizer.sanitize_matched_cars(matched_cars)
    cars_text = _format_matched_cars(sanitized_cars)
    _, wrapped_rag, boundary_directive = PromptSanitizer.wrap_context_boundaries(
        conversation_history, cars_text
    )

    parts: List[str] = [
        f"[当前会话动态状态 | 阶段: {stage.value}]",
        f"客户画像: {profile.model_dump_json()}",
        f"待补充画像字段: {_get_missing_profile_fields(profile)}",
        f"显性需求: {needs.explicit.model_dump_json()}",
        f"隐性需求: {needs.implicit.model_dump_json()}",
        f"待探索需求: {_get_missing_needs_fields(needs)}",
    ]

    if preferences is not None:
        pref_summary = PreferenceEngine.format_for_prompt(preferences)
        if pref_summary:
            parts.append(f"三元偏好权重建模:\n{pref_summary}")

    if pending_confirmation:
        parts.append(f"待客户确认的低置信度变更: {pending_confirmation}")

    parts.append(f"匹配车型与证据:\n{wrapped_rag or cars_text}")
    parts.append(
        f"预约信息: {reservation.model_dump_json()} (待补充: {_get_missing_reservation_fields(reservation)})"
    )

    active_notes = list(system_notes or [])
    if boundary_directive not in active_notes:
        active_notes.append(boundary_directive)

    for card in match_battlecards(conversation_history):
        card_note = card.to_system_note()
        if card_note not in active_notes:
            active_notes.append(card_note)

    if active_notes:
        parts.append("本轮系统指令与近期状态变化：\n" + "\n".join(active_notes))

    return "\n".join(parts)


_PROMPT_TEMPLATE = ChatPromptTemplate.from_messages(
    [
        ("system", "{system_instruction}"),
        MessagesPlaceholder(variable_name="history", optional=True),
        ("human", "{user_input}"),
    ]
)


def _prepare_prompt_inputs(
    stage: Stage,
    conversation_history: str,
    profile: UserProfile,
    needs: VehicleNeeds,
    matched_cars: List[Dict[str, Any]],
    reservation: ReservationInfo,
    system_notes: Optional[List[str]] = None,
    messages: Optional[Sequence[BaseMessage]] = None,
    preferences: Optional[PreferenceModel] = None,
    pending_confirmation: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Build KV-cache-friendly prompt inputs:
    - `system_instruction`: 100% static per stage
    - `history`: micro-compacted message history
    - `user_input`: dynamic context block + current user turn
    """
    system_instruction = get_static_system_instruction(stage)
    dynamic_block = _build_dynamic_context_block(
        stage=stage,
        conversation_history=conversation_history,
        profile=profile,
        needs=needs,
        matched_cars=matched_cars,
        reservation=reservation,
        system_notes=system_notes,
        preferences=preferences,
        pending_confirmation=pending_confirmation,
    )

    if messages:
        msg_list = micro_compact_messages(list(messages))
        if msg_list and isinstance(msg_list[-1], HumanMessage):
            history = msg_list[:-1]
            raw_turn = (
                msg_list[-1].content
                if isinstance(msg_list[-1].content, str)
                else str(msg_list[-1].content)
            )
        else:
            history = msg_list
            raw_turn = "请根据以上信息回复客户。"
    else:
        history = []
        last_user = ""
        for line in reversed((conversation_history or "").splitlines()):
            if line.startswith("user:"):
                last_user = line[len("user:") :].strip()
                break
        if not last_user and conversation_history:
            last_user = conversation_history
        raw_turn = last_user or "请根据以上信息回复客户。"

    user_input = f"{dynamic_block}\n\n[本轮客户发言]\n{raw_turn}"
    return {
        "system_instruction": system_instruction,
        "history": history,
        "user_input": user_input,
    }


def _fallback_response(stage: Stage, profile: UserProfile) -> str:
    name_prefix = f"{profile.name}，" if profile.name else ""
    if stage == Stage.WELCOME:
        return f"{name_prefix}您好！欢迎来到 AutoVend 智能汽车顾问，请问怎么称呼您？"
    return f"{name_prefix}我明白了，请您继续告诉我您的具体购车需求或想了解的车型。"


def build_reply_messages(
    stage: Stage,
    conversation_history: str,
    profile: UserProfile,
    needs: VehicleNeeds,
    matched_cars: List[Dict[str, Any]],
    reservation: ReservationInfo,
    system_notes: Optional[List[str]] = None,
    messages: Optional[Sequence[BaseMessage]] = None,
    preferences: Optional[PreferenceModel] = None,
    pending_confirmation: Optional[Dict[str, Any]] = None,
) -> List[BaseMessage]:
    """Build `[Static SystemMessage, *compacted_history, HumanMessage(dynamic + turn)]`."""
    inputs = _prepare_prompt_inputs(
        stage=stage,
        conversation_history=conversation_history,
        profile=profile,
        needs=needs,
        matched_cars=matched_cars,
        reservation=reservation,
        system_notes=system_notes,
        messages=messages,
        preferences=preferences,
        pending_confirmation=pending_confirmation,
    )
    return _PROMPT_TEMPLATE.format_messages(**inputs)


def generate_reply_with_langchain(
    chat_model: BaseChatModel,
    stage: Stage,
    conversation_history: str,
    profile: UserProfile,
    needs: VehicleNeeds,
    matched_cars: List[Dict[str, Any]],
    reservation: ReservationInfo,
    system_notes: Optional[List[str]] = None,
    messages: Optional[Sequence[BaseMessage]] = None,
) -> str:
    """Generate a customer-facing reply via LangChain LCEL (`Prompt | BaseChatModel | StrOutputParser`)."""
    inputs = _prepare_prompt_inputs(
        stage=stage,
        conversation_history=conversation_history,
        profile=profile,
        needs=needs,
        matched_cars=matched_cars,
        reservation=reservation,
        system_notes=system_notes,
        messages=messages,
    )
    chain = _PROMPT_TEMPLATE | chat_model | StrOutputParser()
    try:
        raw = chain.invoke(inputs)
        cleaned, _ = scrub_think_blocks(raw)
        text = cleaned.strip()
        if not text:
            return _fallback_response(stage, profile)
        return text
    except Exception as exc:
        logger.error(f"LangChain response generation failed at stage {stage.value}: {exc}")
        return _fallback_response(stage, profile)


_OPEN_THINK_RE = re.compile(r"<(think|thought|reasoning)>", re.IGNORECASE)


async def generate_reply_stream_with_langchain(
    chat_model: BaseChatModel,
    stage: Stage,
    conversation_history: str,
    profile: UserProfile,
    needs: VehicleNeeds,
    matched_cars: List[Dict[str, Any]],
    reservation: ReservationInfo,
    system_notes: Optional[List[str]] = None,
    messages: Optional[Sequence[BaseMessage]] = None,
) -> AsyncGenerator[str, None]:
    """Stream response tokens asynchronously via LangChain LCEL `.astream()`, stripping `<think>` blocks."""
    inputs = _prepare_prompt_inputs(
        stage=stage,
        conversation_history=conversation_history,
        profile=profile,
        needs=needs,
        matched_cars=matched_cars,
        reservation=reservation,
        system_notes=system_notes,
        messages=messages,
    )
    chain = _PROMPT_TEMPLATE | chat_model | StrOutputParser()
    emitted = False
    buf = ""
    in_think = False
    think_tag = ""

    try:
        async for chunk in chain.astream(inputs):
            if not chunk:
                continue
            buf += chunk

            while buf:
                if in_think:
                    close_re = re.compile(rf"</{re.escape(think_tag)}>", re.IGNORECASE)
                    m_close = close_re.search(buf)
                    if m_close:
                        buf = buf[m_close.end() :].lstrip("\r\n")
                        in_think = False
                        think_tag = ""
                    else:
                        keep = len(think_tag) + 4
                        if len(buf) > keep:
                            buf = buf[-keep:]
                        break
                else:
                    m_open = _OPEN_THINK_RE.search(buf)
                    if m_open:
                        before = buf[: m_open.start()]
                        if before:
                            emitted = True
                            yield before
                        in_think = True
                        think_tag = m_open.group(1)
                        buf = buf[m_open.end() :]
                    else:
                        lt_idx = buf.rfind("<")
                        if lt_idx != -1 and (len(buf) - lt_idx) <= 12:
                            safe_part = buf[:lt_idx]
                            if safe_part:
                                emitted = True
                                yield safe_part
                            buf = buf[lt_idx:]
                            break
                        else:
                            emitted = True
                            yield buf
                            buf = ""
                            break

        if not in_think and buf:
            emitted = True
            yield buf

        if not emitted:
            yield _fallback_response(stage, profile)
    except Exception as exc:
        logger.error(f"LangChain streaming generation failed at stage {stage.value}: {exc}")
        if not emitted:
            yield _fallback_response(stage, profile)
