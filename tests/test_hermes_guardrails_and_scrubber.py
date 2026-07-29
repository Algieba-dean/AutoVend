"""
Unit tests for ToolLoopGuardrail and ThinkScrubber (tests/test_hermes_guardrails_and_scrubber.py).
"""

from src.agent.tool_guardrails import ToolLoopGuardrail
from src.agent.think_scrubber import scrub_think_blocks


def test_tool_loop_guardrail_exact_repeat():
    """Test ToolLoopGuardrail detecting exact repeat tool invocations."""
    guardrail = ToolLoopGuardrail(exact_repeat_limit=2)

    # First call: OK
    warn1 = guardrail.record_and_evaluate("search_vehicles", {"query": "保时捷 20万"}, success=True)
    assert warn1 is None

    # Second call with exact same args: Trigger熔断 Warning
    warn2 = guardrail.record_and_evaluate("search_vehicles", {"query": "保时捷 20万"}, success=True)
    assert warn2 is not None
    assert "熔断" in warn2 or "重复调用" in warn2


def test_tool_loop_guardrail_repeated_failures():
    """Test ToolLoopGuardrail detecting repeated tool failures."""
    guardrail = ToolLoopGuardrail(same_tool_failure_limit=3)

    guardrail.record_and_evaluate("compare_vehicles", {"car_a": "A"}, success=False)
    guardrail.record_and_evaluate("compare_vehicles", {"car_b": "B"}, success=False)
    warn = guardrail.record_and_evaluate("compare_vehicles", {"car_c": "C"}, success=False)

    assert warn is not None
    assert "连续失败" in warn


def test_think_scrubber():
    """Test scrub_think_blocks isolating <think> tags."""
    raw = "<think>用户想买纯电SUV，我需要核验其预算。</think>推荐您关注问界M7和理想L7。"
    clean, thoughts = scrub_think_blocks(raw)

    assert clean == "推荐您关注问界M7和理想L7。"
    assert "think" in thoughts
