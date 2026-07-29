"""
Chat memory management using LlamaIndex ChatMemoryBuffer.

Provides per-session conversation history with configurable token limits.
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

from llama_index.core.llms import ChatMessage, MessageRole
from llama_index.core.memory import ChatMemoryBuffer

logger = logging.getLogger(__name__)

# Default token limit for memory buffer
DEFAULT_TOKEN_LIMIT = 3000


class ChatMemoryManager:
    """
    Manages per-session chat memory buffers.

    Each session gets its own ChatMemoryBuffer that maintains
    conversation history within a token limit.
    """

    def __init__(self, token_limit: int = DEFAULT_TOKEN_LIMIT):
        self._sessions: Dict[str, ChatMemoryBuffer] = {}
        self._token_limit = token_limit

    def get_or_create(self, session_id: str) -> ChatMemoryBuffer:
        """Get existing memory buffer or create a new one for the session."""
        if session_id not in self._sessions:
            self._sessions[session_id] = ChatMemoryBuffer.from_defaults(
                token_limit=self._token_limit,
            )
            logger.info(f"Created new memory buffer for session {session_id}")
        return self._sessions[session_id]

    def add_message(self, session_id: str, role: MessageRole, content: str) -> None:
        """Add a message to the session's memory buffer."""
        memory = self.get_or_create(session_id)
        memory.put(ChatMessage(role=role, content=content))

    def add_user_message(self, session_id: str, content: str) -> None:
        """Convenience: add a user message."""
        self.add_message(session_id, MessageRole.USER, content)

    def add_assistant_message(self, session_id: str, content: str) -> None:
        """Convenience: add an assistant message."""
        self.add_message(session_id, MessageRole.ASSISTANT, content)

    def get_history(self, session_id: str) -> List[ChatMessage]:
        """Get the chat history for a session."""
        memory = self.get_or_create(session_id)
        return memory.get_all()

    def get_history_as_text(
        self,
        session_id: str,
        summary_history: Optional[List[Dict[str, Any]]] = None,
    ) -> str:
        """Get the chat history formatted as text for prompt injection."""
        history = self.get_history(session_id)
        lines = []
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
            role = "User" if msg.role == MessageRole.USER else "Assistant"
            lines.append(f"{role}: {msg.content}")
        return "\n".join(lines)


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


def compress_history_incrementally(
    llm,
    state,
    history: List[ChatMessage],
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

    # Group ChatMessage into turns (each User message starts a turn)
    turns: List[List[ChatMessage]] = []
    current_turn: List[ChatMessage] = []
    for msg in history:
        if msg.role == MessageRole.USER and current_turn:
            turns.append(current_turn)
            current_turn = []
        current_turn.append(msg)
    if current_turn:
        turns.append(current_turn)

    total_turns = len(turns)
    uncompressed_count = total_turns - state.last_compressed_turn

    # Determine whether compression should trigger
    should_compress = (uncompressed_count >= compress_interval) or (
        stage_changed and uncompressed_count > 0
    )

    if not should_compress:
        return state, None

    start_turn_idx = state.last_compressed_turn

    if stage_changed and uncompressed_count < compress_interval:
        end_turn_idx = total_turns
    else:
        end_turn_idx = start_turn_idx + (uncompressed_count // compress_interval) * compress_interval

    slice_turns = turns[start_turn_idx:end_turn_idx]
    if not slice_turns:
        return state, None

    # Format the uncompressed slice text
    slice_lines = []
    for idx, turn_msgs in enumerate(slice_turns, start=start_turn_idx + 1):
        slice_lines.append(f"--- 第 {idx} 轮 ---")
        for msg in turn_msgs:
            role = "User" if msg.role == MessageRole.USER else "Assistant"
            slice_lines.append(f"{role}: {msg.content}")

    turn_text = "\n".join(slice_lines)
    prompt = SUMMARIZE_TURN_SLICE_PROMPT.format(
        start_turn=start_turn_idx + 1,
        end_turn=end_turn_idx,
        turn_text=turn_text,
    )

    try:
        response = llm.complete(prompt)
        summary_text = getattr(response, "text", str(response)).strip()
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

    # Direction C: Hierarchical summary aggregation if slice limit reached
    if len(state.summary_history) >= max_slices:
        state = _aggregate_hierarchical_summaries(llm, state, fuse_count=max_slices - 1)

    return state, entry


def _aggregate_hierarchical_summaries(llm, state, fuse_count: int = 3):
    """Fuse the oldest `fuse_count` summary slices into a single high-tier summary."""
    if len(state.summary_history) < fuse_count:
        return state

    oldest_slices = state.summary_history[:fuse_count]
    remaining_slices = state.summary_history[fuse_count:]

    slice_descriptions = []
    for item in oldest_slices:
        st = item.get("start_turn")
        et = item.get("end_turn")
        stage_info = f" ({item['stage']})" if item.get("stage") else ""
        slice_descriptions.append(f"• [第 {st}-{et} 轮{stage_info}]: {item.get('summary', '')}")

    slices_text = "\n".join(slice_descriptions)
    prompt = HIERARCHICAL_AGGREGATION_PROMPT.format(slices_text=slices_text)

    try:
        response = llm.complete(prompt)
        aggregated_text = getattr(response, "text", str(response)).strip()
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



    def clear_session(self, session_id: str) -> None:
        """Clear a session's memory buffer."""
        if session_id in self._sessions:
            del self._sessions[session_id]
            logger.info(f"Cleared memory for session {session_id}")

    def has_session(self, session_id: str) -> bool:
        """Check if a session exists."""
        return session_id in self._sessions

    @property
    def active_sessions(self) -> List[str]:
        """List all active session IDs."""
        return list(self._sessions.keys())
