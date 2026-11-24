"""
Incremental & hierarchical conversation summary compression using LangChain messages.

Replaces the legacy LlamaIndex `ChatMemoryBuffer`-based compression helper with
a pure `langchain_core.messages` implementation compatible with LangGraph state.
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage

logger = logging.getLogger(__name__)

SUMMARIZE_TURN_SLICE_PROMPT = """你是一个专业的汽车销售对话总结助手。

请针对以下第 {start_turn} 轮到第 {end_turn} 轮的对话内容提取精简摘要。
请重点保留：
1. 客户表达的核心需求变动、品牌/车型偏好与确定性决议；
2. 客户关注的特定问题或疑虑。

注意：只需总结该切片内的增量信息，保持简明扼要（200字以内），不要包含泛化推测。

对话切片内容：
{turn_text}

请直接输出摘要内容："""

HIERARCHICAL_AGGREGATION_PROMPT = """你是一个专业的汽车销售对话总结助手。

请将以下几段连续的历史对话归档切片摘要，二次融合成一条简明扼要的高阶阶段全局总结。
请重点保留关键事实、确定的选车决定及预约信息，压缩重复细节，字数控制在 200 字以内。

待融合的切片摘要：
{slices_text}

请直接输出融合后的全局高阶摘要内容："""


def _is_user_message(msg: BaseMessage) -> bool:
    if isinstance(msg, HumanMessage):
        return True
    msg_type = getattr(msg, "type", "")
    return msg_type in ("human", "user")


def _invoke_summary_llm(llm: Any, prompt: str) -> str:
    """Invoke either a LangChain BaseChatModel or a duck-typed `.complete()` mock."""
    if hasattr(llm, "invoke") and callable(llm.invoke) and not hasattr(llm, "complete"):
        resp = llm.invoke([HumanMessage(content=prompt)])
        return str(getattr(resp, "content", resp)).strip()
    if hasattr(llm, "complete") and callable(llm.complete):
        resp = llm.complete(prompt)
        return str(getattr(resp, "text", resp)).strip()
    resp = llm.invoke(prompt)
    return str(getattr(resp, "content", resp)).strip()


def format_history_with_summaries(
    history: List[BaseMessage],
    summary_history: Optional[List[Dict[str, Any]]] = None,
) -> str:
    """Format LangChain message history + incremental/hierarchical summaries as text."""
    lines: List[str] = []
    if summary_history:
        lines.append("=== 历史对话增量与高阶归档摘要 ===")
        for item in summary_history:
            start_t = item.get("start_turn", "?")
            end_t = item.get("end_turn", "?")
            summary = item.get("summary", "")
            stage_tag = f" [阶段: {item['stage']}]" if item.get("stage") else ""
            tier_tag = " [高阶总结]" if item.get("is_hierarchical") else ""
            lines.append(f"• [第 {start_t}-{end_t} 轮归档{tier_tag}{stage_tag}]: {summary}")
        lines.append("=== 最新对话上下文 ===")

    for msg in history:
        role = "User" if _is_user_message(msg) else "Assistant"
        content = msg.content if isinstance(msg.content, str) else str(msg.content)
        lines.append(f"{role}: {content}")
    return "\n".join(lines)


def compress_history_incrementally(
    llm: Any,
    state: Any,
    history: List[BaseMessage],
    compress_interval: int = 6,
    stage_changed: bool = False,
    current_stage: str = "",
    max_slices: int = 4,
) -> Tuple[Any, Optional[Dict[str, Any]]]:
    """
    Incremental & Hierarchical conversation summary compression (Optimizations A & C).

    - Direction A (Stage-driven dynamic slicing): If `stage_changed` is True and there
      are uncompressed turns, triggers a summary slice even if `compress_interval` isn't met.
    - Direction C (Hierarchical aggregation): When `len(state.summary_history)` reaches
      `max_slices`, recursively fuses the oldest slices into a single high-tier summary.
    """
    if llm is None:
        return state, None

    turns: List[List[BaseMessage]] = []
    current_turn: List[BaseMessage] = []
    for msg in history:
        if _is_user_message(msg) and current_turn:
            turns.append(current_turn)
            current_turn = []
        current_turn.append(msg)
    if current_turn:
        turns.append(current_turn)

    total_turns = len(turns)
    uncompressed_count = total_turns - state.last_compressed_turn

    should_compress = (uncompressed_count >= compress_interval) or (
        stage_changed and uncompressed_count > 0
    )
    if not should_compress:
        return state, None

    start_turn_idx = state.last_compressed_turn
    if stage_changed and uncompressed_count < compress_interval:
        end_turn_idx = total_turns
    else:
        end_turn_idx = (
            start_turn_idx + (uncompressed_count // compress_interval) * compress_interval
        )

    slice_turns = turns[start_turn_idx:end_turn_idx]
    if not slice_turns:
        return state, None

    slice_lines: List[str] = []
    for idx, turn_msgs in enumerate(slice_turns, start=start_turn_idx + 1):
        slice_lines.append(f"--- 第 {idx} 轮 ---")
        for msg in turn_msgs:
            role = "User" if _is_user_message(msg) else "Assistant"
            content = msg.content if isinstance(msg.content, str) else str(msg.content)
            slice_lines.append(f"{role}: {content}")

    turn_text = "\n".join(slice_lines)
    prompt = SUMMARIZE_TURN_SLICE_PROMPT.format(
        start_turn=start_turn_idx + 1,
        end_turn=end_turn_idx,
        turn_text=turn_text,
    )

    try:
        summary_text = _invoke_summary_llm(llm, prompt)
    except Exception as exc:
        logger.warning(f"Incremental summary compression failed: {exc}")
        return state, None

    entry: Dict[str, Any] = {
        "start_turn": start_turn_idx + 1,
        "end_turn": end_turn_idx,
        "summary": summary_text,
    }
    if current_stage:
        entry["stage"] = current_stage

    state.summary_history.append(entry)
    state.last_compressed_turn = end_turn_idx
    logger.info(
        f"[{state.session_id}] Incremental summary created for turns "
        f"{entry['start_turn']}-{entry['end_turn']}: {summary_text[:60]}..."
    )

    if len(state.summary_history) >= max_slices:
        state = _aggregate_hierarchical_summaries(llm, state, fuse_count=max_slices - 1)

    return state, entry


def _aggregate_hierarchical_summaries(llm: Any, state: Any, fuse_count: int = 3) -> Any:
    """Fuse the oldest `fuse_count` summary slices into a single high-tier summary."""
    if len(state.summary_history) < fuse_count:
        return state

    oldest_slices = state.summary_history[:fuse_count]
    remaining_slices = state.summary_history[fuse_count:]

    slice_descriptions: List[str] = []
    for item in oldest_slices:
        st = item.get("start_turn")
        et = item.get("end_turn")
        stage_info = f" ({item['stage']})" if item.get("stage") else ""
        slice_descriptions.append(f"• [第 {st}-{et} 轮{stage_info}]: {item.get('summary', '')}")

    slices_text = "\n".join(slice_descriptions)
    prompt = HIERARCHICAL_AGGREGATION_PROMPT.format(slices_text=slices_text)

    try:
        aggregated_text = _invoke_summary_llm(llm, prompt)
    except Exception as exc:
        logger.warning(f"Hierarchical summary aggregation failed: {exc}")
        return state

    start_turn = oldest_slices[0].get("start_turn", 1)
    end_turn = oldest_slices[-1].get("end_turn", 1)

    aggregated_entry = {
        "start_turn": start_turn,
        "end_turn": end_turn,
        "summary": aggregated_text,
        "is_hierarchical": True,
    }

    state.summary_history = [aggregated_entry] + remaining_slices
    logger.info(
        f"[{state.session_id}] Hierarchical summary created for turns "
        f"{start_turn}-{end_turn}: {aggregated_text[:60]}..."
    )
    return state


__all__ = [
    "AIMessage",
    "HumanMessage",
    "compress_history_incrementally",
    "format_history_with_summaries",
]
