"""
LangChain LCEL chains for AutoVend response generation (sync & async streaming).
"""

import logging
import re
from typing import Any, AsyncGenerator, Dict, List, Optional, Sequence

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import BaseMessage, HumanMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from src.agent.response_generator import _build_stage_prompt
from src.agent.schemas import (
    ReservationInfo,
    Stage,
    UserProfile,
    VehicleNeeds,
)
from src.agent.think_scrubber import scrub_think_blocks

logger = logging.getLogger(__name__)

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
) -> Dict[str, Any]:
    """Split stage instructions (System), dialogue turns (MessagesPlaceholder), and current turn (Human)."""
    full_prompt = _build_stage_prompt(
        stage=stage,
        conversation_history=conversation_history,
        profile=profile,
        needs=needs,
        matched_cars=matched_cars,
        reservation=reservation,
        system_notes=system_notes,
    )
    # Strip trailing "Conversation so far:\n..." from system instruction when structured messages are supplied
    if messages:
        marker = "\n\nConversation so far:"
        if marker in full_prompt:
            before_conv, after_conv = full_prompt.split(marker, 1)
            notes_marker = "\n\n本轮系统指令与近期状态变化："
            if notes_marker in after_conv:
                _, notes_part = after_conv.split(notes_marker, 1)
                system_instruction = f"{before_conv}{notes_marker}{notes_part}"
            else:
                system_instruction = before_conv
        else:
            system_instruction = full_prompt

        msg_list = list(messages)
        if msg_list and isinstance(msg_list[-1], HumanMessage):
            history = msg_list[:-1]
            user_input = (
                msg_list[-1].content
                if isinstance(msg_list[-1].content, str)
                else str(msg_list[-1].content)
            )
        else:
            history = msg_list
            user_input = conversation_history or "请继续。"
    else:
        system_instruction = full_prompt
        history = []
        # Extract last user turn if present in plain transcript, else provide a concise prompt
        last_user = ""
        for line in reversed((conversation_history or "").splitlines()):
            if line.startswith("user:"):
                last_user = line[len("user:") :].strip()
                break
        user_input = last_user or "请根据以上信息回复客户。"

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
) -> List[BaseMessage]:
    """Build structured `[SystemMessage, *history, HumanMessage]` for LangGraph generation nodes."""
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
