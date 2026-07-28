"""
Unit tests for incremental turn-based, stage-driven, and hierarchical conversation summary compression.
"""

from unittest.mock import MagicMock

from llama_index.core.llms import ChatMessage, MessageRole

from src.agent.memory import ChatMemoryManager, compress_history_incrementally
from src.agent.schemas import SessionState


def test_compress_history_incrementally_threshold():
    state = SessionState(session_id="test_sess_1")
    mock_llm = MagicMock()
    mock_llm.complete.return_value = "客户预算30万，看重续航与安全。"

    # Build 6 turns of messages (12 ChatMessages)
    messages = []
    for i in range(1, 7):
        messages.append(ChatMessage(role=MessageRole.USER, content=f"这是第{i}轮问题"))
        messages.append(ChatMessage(role=MessageRole.ASSISTANT, content=f"这是第{i}轮回答"))

    # Compress at interval 6
    updated_state, entry = compress_history_incrementally(
        llm=mock_llm,
        state=state,
        history=messages,
        compress_interval=6,
    )

    assert entry is not None
    assert entry["start_turn"] == 1
    assert entry["end_turn"] == 6
    assert entry["summary"] == "客户预算30万，看重续航与安全。"
    assert updated_state.last_compressed_turn == 6
    assert len(updated_state.summary_history) == 1
    mock_llm.complete.assert_called_once()


def test_compress_history_incrementally_no_recompression_on_second_batch():
    state = SessionState(session_id="test_sess_2")
    mock_llm = MagicMock()
    mock_llm.complete.side_effect = [
        "第一批摘要：讨论了价格和新能源",
        "第二批摘要：确认了试驾时间和地点",
    ]

    # Build 12 turns of messages (24 ChatMessages)
    messages = []
    for i in range(1, 13):
        messages.append(ChatMessage(role=MessageRole.USER, content=f"这是第{i}轮问题"))
        messages.append(ChatMessage(role=MessageRole.ASSISTANT, content=f"这是第{i}轮回答"))

    # First compression (only first 6 turns)
    state, entry1 = compress_history_incrementally(
        llm=mock_llm,
        state=state,
        history=messages[:12],  # turns 1-6
        compress_interval=6,
    )
    assert entry1["start_turn"] == 1
    assert entry1["end_turn"] == 6
    assert state.last_compressed_turn == 6

    # Second compression (turns 1-12 available, but turns 1-6 already compressed!)
    state, entry2 = compress_history_incrementally(
        llm=mock_llm,
        state=state,
        history=messages,  # all 12 turns
        compress_interval=6,
    )
    assert entry2["start_turn"] == 7
    assert entry2["end_turn"] == 12
    assert state.last_compressed_turn == 12
    assert len(state.summary_history) == 2
    assert state.summary_history[0]["summary"] == "第一批摘要：讨论了价格和新能源"
    assert state.summary_history[1]["summary"] == "第二批摘要：确认了试驾时间和地点"

    # LLM should have been called twice (once for 1-6, once for 7-12)
    assert mock_llm.complete.call_count == 2
    prompt_arg = mock_llm.complete.call_args_list[1][0][0]
    # Check that prompt for 2nd call ONLY contains turns 7-12, NOT turns 1-6!
    assert "第 7 轮" in prompt_arg
    assert "第 12 轮" in prompt_arg
    assert "第 1 轮" not in prompt_arg


def test_compress_history_stage_driven_direction_a():
    """Direction A: Stage transition triggers compression even if compress_interval isn't reached."""
    state = SessionState(session_id="test_sess_3")
    mock_llm = MagicMock()
    mock_llm.complete.return_value = "画像阶段小结：了解了预算与用车需求"

    # Build 3 turns of messages
    messages = []
    for i in range(1, 4):
        messages.append(ChatMessage(role=MessageRole.USER, content=f"这是第{i}轮问题"))
        messages.append(ChatMessage(role=MessageRole.ASSISTANT, content=f"这是第{i}轮回答"))

    # Stage changed at turn 3 (before interval 6)
    state, entry = compress_history_incrementally(
        llm=mock_llm,
        state=state,
        history=messages,
        compress_interval=6,
        stage_changed=True,
        current_stage="profile_analysis",
    )

    assert entry is not None
    assert entry["start_turn"] == 1
    assert entry["end_turn"] == 3
    assert entry["stage"] == "profile_analysis"
    assert state.last_compressed_turn == 3
    assert len(state.summary_history) == 1


def test_hierarchical_summary_aggregation_direction_c():
    """Direction C: Max slices reached triggers recursive hierarchical aggregation."""
    state = SessionState(session_id="test_sess_4")
    mock_llm = MagicMock()
    mock_llm.complete.side_effect = [
        "切片1摘要",
        "切片2摘要",
        "切片3摘要",
        "高阶归档全局融合摘要（覆盖1-9轮）",
    ]

    messages = []
    for i in range(1, 10):
        messages.append(ChatMessage(role=MessageRole.USER, content=f"这是第{i}轮问题"))
        messages.append(ChatMessage(role=MessageRole.ASSISTANT, content=f"这是第{i}轮回答"))

    # Produce 3 slices with compress_interval=3 and max_slices=3
    # 1st slice: turns 1-3
    state, _ = compress_history_incrementally(
        llm=mock_llm, state=state, history=messages[:6], compress_interval=3, max_slices=3
    )
    # 2nd slice: turns 4-6
    state, _ = compress_history_incrementally(
        llm=mock_llm, state=state, history=messages[:12], compress_interval=3, max_slices=3
    )
    # 3rd slice: turns 7-9 -> triggers hierarchical aggregation of oldest 2 slices
    state, _ = compress_history_incrementally(
        llm=mock_llm, state=state, history=messages, compress_interval=3, max_slices=3
    )

    # Check that summary_history was aggregated and contains the hierarchical summary
    assert len(state.summary_history) == 2  # Aggregated (1-6) + Slice 3 (7-9)
    assert state.summary_history[0]["is_hierarchical"] is True
    assert state.summary_history[0]["start_turn"] == 1
    assert state.summary_history[0]["end_turn"] == 6
    assert state.summary_history[0]["summary"] == "高阶归档全局融合摘要（覆盖1-9轮）"


def test_get_history_as_text_with_summary_history():
    memory = ChatMemoryManager()
    memory.add_user_message("s1", "你好，我想买车")
    memory.add_assistant_message("s1", "您好！请问预算多少？")

    summary_history = [
        {
            "start_turn": 1,
            "end_turn": 6,
            "stage": "profile_analysis",
            "summary": "第一阶段聊了预算和喜好",
        },
        {
            "start_turn": 1,
            "end_turn": 12,
            "is_hierarchical": True,
            "summary": "早期轮次高阶总结",
        },
    ]

    formatted_text = memory.get_history_as_text("s1", summary_history=summary_history)
    assert "=== 历史对话增量与高阶归档摘要 ===" in formatted_text
    assert "• [第 1-6 轮归档 [阶段: profile_analysis]]: 第一阶段聊了预算和喜好" in formatted_text
    assert "• [第 1-12 轮归档 [高阶总结]]: 早期轮次高阶总结" in formatted_text
    assert "User: 你好，我想买车" in formatted_text
