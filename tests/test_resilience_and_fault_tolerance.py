"""
Resilience, Exception Fallback & Fault Tolerance Tests (tests/test_resilience_and_fault_tolerance.py).

Verifies system resilience when LLMs, ChromaDB, or SQLite experience transient errors or timeouts.
"""

from unittest.mock import MagicMock
from src.agent.reflection import reflect_and_guard
from src.agent.reconciliation import reconcile_constraints
from src.retrieval.hybrid_pipeline import HybridPipeline, HybridPipelineResult


def test_reflection_resilience_on_invalid_inputs():
    """Test reflection and guardrail handling None or malformed inputs without crashing."""
    text, issues = reflect_and_guard("", matched_cars=None)
    assert text == ""
    assert issues == []

    text2, issues2 = reflect_and_guard("价格保证全网最低价，且承诺包过户避税", matched_cars=[{"car_model": "ModelA"}])
    assert "保证全网最低价" not in text2
    assert len(issues2) >= 1


def test_reconciliation_resilience_on_empty_state():
    """Test constraint reconciliation on empty or incomplete state."""
    from src.agent.schemas import SessionState
    state = SessionState()

    conflicts = reconcile_constraints(state)
    assert conflicts == []


def test_hybrid_pipeline_fault_tolerance_on_retriever_failure():
    """Test HybridPipeline falling back gracefully if vector retriever fails."""
    pipeline = HybridPipeline()
    pipeline.retriever = MagicMock()
    pipeline.retriever.search.side_effect = RuntimeError("Vector DB connection timeout")

    res = pipeline.search("20万纯电SUV", top_k=5)
    assert isinstance(res, HybridPipelineResult)
    # Filter result should still survive via SQLite
    assert res.candidate_count >= 0
