"""
Pytest-based performance evaluation tests.

Runs all 24 dialogue scenarios through the agent and asserts KPI targets.
Each test produces detailed scoring; results are persisted to eval_results/.
"""

import pytest

from tests.performance.eval_harness import evaluate_dialogue, run_full_evaluation, save_report
from tests.performance.scenarios import (
    ADVERSARIAL_SCENARIOS,
    BILINGUAL_SCENARIOS,
    EDGE_CASE_SCENARIOS,
    FULL_FUNNEL_SCENARIOS,
    NORMAL_SCENARIOS,
)

# ── Per-Dialogue Tests ────────────────────────────────────────────────────────


class TestNormalDialogues:
    """Normal happy-path dialogues must score well across all dimensions."""

    @pytest.mark.parametrize("scenario", NORMAL_SCENARIOS, ids=[s["id"] for s in NORMAL_SCENARIOS])
    def test_stage_accuracy(self, scenario):
        sc = evaluate_dialogue(scenario)
        assert sc.stage_accuracy >= 0.60, (
            f"[{scenario['id']}] stage_accuracy={sc.stage_accuracy:.0%} — target ≥ 60%"
        )

    @pytest.mark.parametrize("scenario", NORMAL_SCENARIOS, ids=[s["id"] for s in NORMAL_SCENARIOS])
    def test_response_generation(self, scenario):
        sc = evaluate_dialogue(scenario)
        assert sc.response_generation_rate == 1.0, (
            f"[{scenario['id']}] response_rate={sc.response_generation_rate:.0%} — target 100%"
        )

    @pytest.mark.parametrize("scenario", NORMAL_SCENARIOS, ids=[s["id"] for s in NORMAL_SCENARIOS])
    def test_overall_score(self, scenario):
        sc = evaluate_dialogue(scenario)
        assert sc.overall_score >= 40.0, (
            f"[{scenario['id']}] overall={sc.overall_score:.1f} — target ≥ 40"
        )

    @pytest.mark.parametrize("scenario", NORMAL_SCENARIOS, ids=[s["id"] for s in NORMAL_SCENARIOS])
    def test_professionalism(self, scenario):
        sc = evaluate_dialogue(scenario)
        assert sc.avg_professionalism >= 30.0, (
            f"[{scenario['id']}] professionalism={sc.avg_professionalism:.1f} — target ≥ 30"
        )


class TestEdgeCaseDialogues:
    """Edge cases: agent should remain stable and not crash."""

    @pytest.mark.parametrize(
        "scenario", EDGE_CASE_SCENARIOS, ids=[s["id"] for s in EDGE_CASE_SCENARIOS]
    )
    def test_no_crash(self, scenario):
        sc = evaluate_dialogue(scenario)
        assert sc.response_generation_rate == 1.0, (
            f"[{scenario['id']}] agent crashed or produced empty response"
        )

    @pytest.mark.parametrize(
        "scenario", EDGE_CASE_SCENARIOS, ids=[s["id"] for s in EDGE_CASE_SCENARIOS]
    )
    def test_overall_score(self, scenario):
        sc = evaluate_dialogue(scenario)
        # Edge cases have lower bar
        assert sc.overall_score >= 15.0, (
            f"[{scenario['id']}] overall={sc.overall_score:.1f} — target ≥ 15 (edge case)"
        )


class TestAdversarialDialogues:
    """Adversarial inputs: agent must not crash, must stay professional."""

    @pytest.mark.parametrize(
        "scenario", ADVERSARIAL_SCENARIOS, ids=[s["id"] for s in ADVERSARIAL_SCENARIOS]
    )
    def test_no_crash(self, scenario):
        sc = evaluate_dialogue(scenario)
        assert sc.response_generation_rate == 1.0, (
            f"[{scenario['id']}] agent crashed on adversarial input"
        )

    @pytest.mark.parametrize(
        "scenario", ADVERSARIAL_SCENARIOS, ids=[s["id"] for s in ADVERSARIAL_SCENARIOS]
    )
    def test_stays_professional(self, scenario):
        sc = evaluate_dialogue(scenario)
        assert sc.avg_professionalism >= 25.0, (
            f"[{scenario['id']}] professionalism={sc.avg_professionalism:.1f} on adversarial input"
        )


class TestBilingualDialogues:
    """Bilingual: agent must handle mixed-language well."""

    @pytest.mark.parametrize(
        "scenario", BILINGUAL_SCENARIOS, ids=[s["id"] for s in BILINGUAL_SCENARIOS]
    )
    def test_response_generation(self, scenario):
        sc = evaluate_dialogue(scenario)
        assert sc.response_generation_rate == 1.0

    @pytest.mark.parametrize(
        "scenario", BILINGUAL_SCENARIOS, ids=[s["id"] for s in BILINGUAL_SCENARIOS]
    )
    def test_overall_score(self, scenario):
        sc = evaluate_dialogue(scenario)
        assert sc.overall_score >= 35.0, (
            f"[{scenario['id']}] overall={sc.overall_score:.1f} — target ≥ 35 (bilingual)"
        )


class TestFullFunnelDialogues:
    """Full funnel: complete journey should score high."""

    @pytest.mark.parametrize(
        "scenario", FULL_FUNNEL_SCENARIOS, ids=[s["id"] for s in FULL_FUNNEL_SCENARIOS]
    )
    def test_conversion_score(self, scenario):
        sc = evaluate_dialogue(scenario)
        assert sc.conversion_score >= 40.0, (
            f"[{scenario['id']}] conversion={sc.conversion_score:.1f} — target ≥ 40"
        )

    @pytest.mark.parametrize(
        "scenario", FULL_FUNNEL_SCENARIOS, ids=[s["id"] for s in FULL_FUNNEL_SCENARIOS]
    )
    def test_task_completion(self, scenario):
        sc = evaluate_dialogue(scenario)
        assert sc.task_completion_score >= 40.0, (
            f"[{scenario['id']}] task_completion={sc.task_completion_score:.1f} — target ≥ 40"
        )


# ── Aggregate KPI Tests ──────────────────────────────────────────────────────


class TestAggregateKPIs:
    """Aggregate KPI targets across all scenarios."""

    def test_aggregate_stage_accuracy(self):
        report = run_full_evaluation()
        assert report.avg_stage_accuracy >= 50.0, (
            f"Aggregate stage accuracy={report.avg_stage_accuracy:.1f}% — target ≥ 50%"
        )

    def test_aggregate_overall_score(self):
        report = run_full_evaluation()
        assert report.avg_overall >= 30.0, (
            f"Aggregate overall={report.avg_overall:.1f} — target ≥ 30"
        )

    def test_aggregate_professionalism(self):
        report = run_full_evaluation()
        assert report.avg_professionalism >= 25.0, (
            f"Aggregate professionalism={report.avg_professionalism:.1f} — target ≥ 25"
        )

    def test_100_percent_response_rate(self):
        """Every single turn across all scenarios must produce a response."""
        report = run_full_evaluation()
        for sc in report.scorecards:
            assert sc.response_generation_rate == 1.0, (
                f"[{sc.dialogue_id}] response_rate={sc.response_generation_rate:.0%}"
            )

    def test_save_results(self):
        """Run full evaluation and persist results."""
        report = run_full_evaluation()
        filepath = save_report(report, "eval_latest.json")
        assert filepath.exists()
        assert filepath.stat().st_size > 100

    def test_latency_all_under_50ms(self):
        """All turns with mock LLM should be < 50ms."""
        report = run_full_evaluation()
        for sc in report.scorecards:
            assert sc.latency.p95 < 50.0, (
                f"[{sc.dialogue_id}] p95={sc.latency.p95:.1f}ms — target < 50ms"
            )
