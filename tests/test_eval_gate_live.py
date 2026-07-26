"""
The evaluation gate against the real index.

This is the test that would catch an actual retrieval regression — everything
in tests/test_eval_gate.py stubs the retrieval away to test the gate's own
logic. Marked `slow` because it loads BGE-M3 and runs all 116 golden queries.

Run with:  pytest -m slow tests/test_eval_gate_live.py
"""

import pytest

from src.eval.gate import BASELINES, PRODUCTION_SYSTEM, GateFailure, check

pytestmark = pytest.mark.slow


@pytest.fixture(scope="module")
def indices_available():
    """Skip rather than fail when the machine has no built index."""
    from src.filter.vehicle_db import VehicleDB

    if VehicleDB().count() == 0:
        pytest.skip("vehicle catalogue is empty — run `python -m src.main build-index`")

    from src.rag.vector_store import ChromaVectorStore

    try:
        if ChromaVectorStore().collection.count() == 0:
            pytest.skip("vector index is empty — run `python -m src.main build-index`")
    except Exception as exc:  # pragma: no cover - environment-dependent
        pytest.skip(f"vector store unavailable: {exc}")


def test_production_system_meets_its_baseline(indices_available):
    comparison = check(PRODUCTION_SYSTEM)

    for metric, row in comparison.items():
        assert row["measured"] >= row["floor"], (
            f"{metric} regressed: {row['measured']} < {row['floor']}"
        )


def test_gate_rejects_an_unreachable_baseline(indices_available):
    """
    A gate that cannot go red is decoration. This drives the real evaluation
    against a baseline nothing could meet and asserts it actually fails.
    """
    impossible = {metric: 0.999 for metric in BASELINES[PRODUCTION_SYSTEM]}

    with pytest.raises(GateFailure, match="regressed"):
        check(PRODUCTION_SYSTEM, baselines=impossible)


def test_fusion_still_beats_the_pipeline_it_replaced(indices_available):
    """
    The reason fusion is the production path: adding the sparse arm and RRF
    measurably beats the dense-only hybrid it replaced. If this stops holding,
    the extra index is no longer paying for itself.
    """
    fusion = check("fusion")["capped_recall@3"]["measured"]
    hybrid = check("hybrid")["capped_recall@3"]["measured"]

    assert fusion > hybrid, f"fusion {fusion} no longer beats hybrid {hybrid}"
