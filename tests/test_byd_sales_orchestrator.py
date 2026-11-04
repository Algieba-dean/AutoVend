"""
Unit tests for BYD In-Cabin Sales Orchestrator & Expert Subagents (src/agent/).
"""

from unittest.mock import MagicMock

from src.agent.orchestrator import SalesOrchestrator
from src.agent.schemas import SessionState
from src.agent.subagents.comparison import ModelComparisonSubagent
from src.agent.subagents.dispatcher import SubagentDispatcher
from src.agent.subagents.finance import FinancialCalculatorSubagent
from src.agent.subagents.test_drive import TestDriveSchedulerSubagent


def test_anchor_vehicle_context_initialization():
    state = SessionState(session_id="sess_anchor_1")
    assert state.anchor_vehicle.brand == "BYD"
    assert state.anchor_vehicle.model_name == "BYD-Han EV"
    assert "刀片电池" in state.anchor_vehicle.powertrain


def test_model_comparison_subagent():
    subagent = ModelComparisonSubagent()

    # Compare Han vs Seal
    ctx_seal = {
        "anchor_vehicle": {"model_name": "BYD-Han EV"},
        "user_message": "我想对比一下这台汉EV和海豹有什么区别？",
    }
    res_seal = subagent.run(ctx_seal["user_message"], ctx_seal)
    assert res_seal.success is True
    assert "海豹" in res_seal.conclusion
    assert "行政C级" in res_seal.conclusion or "豪华" in res_seal.conclusion

    # Compare BYD vs Tesla
    ctx_tesla = {
        "anchor_vehicle": {"model_name": "BYD-Han EV"},
        "user_message": "这车比Model 3好在哪？",
    }
    res_tesla = subagent.run(ctx_tesla["user_message"], ctx_tesla)
    assert res_tesla.success is True
    assert "特斯拉" in res_tesla.conclusion
    assert "刀片电池" in res_tesla.conclusion


def test_financial_calculator_subagent():
    subagent = FinancialCalculatorSubagent()
    ctx = {
        "anchor_vehicle": {"price_guidance": "20.98万元"},
        "user_message": "首付一成大概多少，有免息吗？",
    }
    res = subagent.run(ctx["user_message"], ctx)
    assert res.success is True
    assert "24 期 0 息" in res.conclusion
    assert "置换补贴" in res.conclusion


def test_test_drive_scheduler_subagent():
    subagent = TestDriveSchedulerSubagent()
    ctx = {
        "anchor_vehicle": {"model_name": "BYD-Han EV"},
        "user_message": "我想试驾一下这台车怎么排期？",
    }
    res = subagent.run(ctx["user_message"], ctx)
    assert res.success is True
    assert "推荐体验路线" in res.conclusion
    assert "12 公里" in res.conclusion


def test_subagent_dispatcher_auto_dispatch():
    dispatcher = SubagentDispatcher()
    context = {"anchor_vehicle": {"model_name": "BYD-Han EV", "price_guidance": "20.98万"}}

    # Message asking for both comparison and financial loan
    msg = "这台车跟特斯拉比怎么样？如果办分期月供多少？"
    results = dispatcher.auto_dispatch(msg, context)
    assert len(results) >= 2
    names = [r.subagent_name for r in results]
    assert "model_comparison_subagent" in names
    assert "financial_calculator_subagent" in names


def test_sales_orchestrator_observe_and_state_compact():
    mock_llm = MagicMock()
    # Mock LLM calls
    mock_response = MagicMock()
    mock_response.text = '{"needs": {}}'
    mock_llm.complete.return_value = mock_response

    orchestrator = SalesOrchestrator(llm=mock_llm)
    state = SessionState(session_id="sess_orch_1")

    # When user asks comparison, orchestrator automatically dispatches subagent
    # and appends conclusion to state.system_notes
    state = orchestrator.observe(state, "这台汉EV比起海豹有哪些优势？")
    assert any("海豹" in note for note in state.system_notes)

    # Test state compacting
    for i in range(7):
        orchestrator.memory.add_user_message(state.session_id, f"第{i}轮对话")
        orchestrator.memory.add_assistant_message(state.session_id, f"系统回复{i}")

    state = orchestrator.compact_state(state, threshold_turns=6)
    assert len(state.summary_history) > 0


def test_multi_target_comparison():
    subagent = ModelComparisonSubagent()
    ctx = {
        "anchor_vehicle": {"model_name": "BYD-Han EV"},
        "user_message": "请对比一下汉EV和特斯拉Model 3，顺便说说和海豹的区别",
    }
    res = subagent.run(ctx["user_message"], ctx)
    assert res.success is True
    assert "海豹" in res.conclusion
    assert "特斯拉" in res.conclusion
    assert "专家对比建议" in res.conclusion


def test_orchestrator_idempotent_anchor_notes():
    mock_llm = MagicMock()
    mock_response = MagicMock()
    mock_response.text = "您好！"
    mock_llm.complete.return_value = mock_response

    orchestrator = SalesOrchestrator(llm=mock_llm)
    state = SessionState(session_id="sess_orch_idem")

    # Call respond twice
    res1 = orchestrator.respond(state)
    res2 = orchestrator.respond(res1.session_state)

    # Ensure anchor note is not duplicated in system_notes
    anchor_notes = [n for n in res2.session_state.system_notes if "【当前座舱展车主锚点】" in n]
    assert len(anchor_notes) <= 1


def test_orchestrator_streaming_and_stage_governance():
    mock_llm = MagicMock()
    mock_llm.stream_complete.return_value = [MagicMock(delta="比亚迪"), MagicMock(delta="欢迎您")]

    orchestrator = SalesOrchestrator(llm=mock_llm)
    state = SessionState(session_id="sess_orch_stream")

    events = list(orchestrator.respond_stream(state))
    event_types = [e[0] for e in events]
    assert "metadata" in event_types
    assert "delta" in event_types
    assert "done" in event_types
