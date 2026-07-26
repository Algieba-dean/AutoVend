"""
Tests for the CI evaluation gate.

Two things matter about a gate: it fails when quality drops, and it does not
fail for any other reason. A gate that cannot go red is decoration, so the
red path is tested as carefully as the green one.

The retrieval systems are stubbed — running the real index here would make the
unit suite depend on a 2GB model. `tests/test_eval_gate_live.py` covers the
real thing behind the `slow` marker.
"""

import pytest

from src.eval import gate
from src.eval.gate import BASELINES, PRODUCTION_SYSTEM, GateFailure, check


@pytest.fixture
def stub_evaluation(monkeypatch):
    """Replace golden-set loading and system evaluation with fixed values."""

    def install(overall):
        monkeypatch.setattr(gate, "load_golden_set", lambda: ["q"] * 116)
        monkeypatch.setattr(
            gate, "evaluate_system", lambda system, queries: {"overall": dict(overall)}
        )

    return install


class TestBaselines:
    def test_production_system_has_a_baseline(self):
        assert PRODUCTION_SYSTEM in BASELINES

    def test_every_baseline_is_a_plausible_score(self):
        for system, metrics in BASELINES.items():
            for metric, value in metrics.items():
                assert 0.0 <= value <= 1.0, f"{system}.{metric} = {value} is not a 0-1 score"

    def test_all_systems_gate_the_same_metrics(self):
        """Otherwise an A/B between two systems compares different things."""
        metric_sets = {frozenset(m) for m in BASELINES.values()}

        assert len(metric_sets) == 1

    def test_production_baseline_beats_the_structured_filter(self):
        """
        Sanity check on the recorded numbers: the full pipeline must be worth
        more than its own pre-filter stage, or the ranking layers add nothing.
        """
        assert (
            BASELINES[PRODUCTION_SYSTEM]["capped_recall@3"] > BASELINES["filter"]["capped_recall@3"]
        )


class TestCheck:
    def test_passes_when_metrics_match_the_baseline(self, stub_evaluation):
        stub_evaluation(BASELINES[PRODUCTION_SYSTEM])

        comparison = check(PRODUCTION_SYSTEM)

        assert set(comparison) == set(BASELINES[PRODUCTION_SYSTEM])
        assert all(row["delta"] == 0.0 for row in comparison.values())

    def test_passes_when_metrics_improve(self, stub_evaluation):
        improved = {k: min(1.0, v + 0.05) for k, v in BASELINES[PRODUCTION_SYSTEM].items()}
        stub_evaluation(improved)

        comparison = check(PRODUCTION_SYSTEM)

        assert all(row["delta"] > 0 for row in comparison.values())

    def test_tolerates_a_small_dip(self, stub_evaluation):
        """Rebuilding the index or breaking a tie differently must not go red."""
        dipped = {k: v - gate.TOLERANCE / 2 for k, v in BASELINES[PRODUCTION_SYSTEM].items()}
        stub_evaluation(dipped)

        check(PRODUCTION_SYSTEM)  # does not raise

    def test_fails_when_a_metric_drops_past_tolerance(self, stub_evaluation):
        regressed = dict(BASELINES[PRODUCTION_SYSTEM])
        regressed["capped_recall@3"] -= gate.TOLERANCE + 0.01
        stub_evaluation(regressed)

        with pytest.raises(GateFailure, match="capped_recall@3"):
            check(PRODUCTION_SYSTEM)

    def test_failure_message_names_every_regressed_metric(self, stub_evaluation):
        stub_evaluation({k: 0.0 for k in BASELINES[PRODUCTION_SYSTEM]})

        with pytest.raises(GateFailure) as exc:
            check(PRODUCTION_SYSTEM)

        for metric in BASELINES[PRODUCTION_SYSTEM]:
            assert metric in str(exc.value)

    def test_missing_metric_is_treated_as_zero(self, stub_evaluation):
        """A renamed metric must fail loudly, not silently skip its check."""
        stub_evaluation({})

        with pytest.raises(GateFailure):
            check(PRODUCTION_SYSTEM)

    def test_accepts_explicit_baselines(self, stub_evaluation):
        stub_evaluation({"capped_recall@3": 0.5})

        check(PRODUCTION_SYSTEM, baselines={"capped_recall@3": 0.4})

        with pytest.raises(GateFailure):
            check(PRODUCTION_SYSTEM, baselines={"capped_recall@3": 0.9})

    def test_unknown_system_raises(self, stub_evaluation):
        stub_evaluation({})

        with pytest.raises(KeyError):
            check("nonexistent")


class TestMain:
    def test_exit_zero_on_pass(self, stub_evaluation, capsys):
        stub_evaluation(BASELINES[PRODUCTION_SYSTEM])

        assert gate.main([]) == 0
        assert "PASS" in capsys.readouterr().out

    def test_exit_one_on_regression(self, stub_evaluation, capsys):
        stub_evaluation({k: 0.0 for k in BASELINES[PRODUCTION_SYSTEM]})

        assert gate.main([]) == 1
        assert "FAIL" in capsys.readouterr().err

    def test_update_baseline_prints_measured_values(self, stub_evaluation, capsys):
        stub_evaluation({k: 0.5 for k in BASELINES[PRODUCTION_SYSTEM]})

        assert gate.main(["--update-baseline"]) == 0
        out = capsys.readouterr().out
        assert f'"{PRODUCTION_SYSTEM}"' in out
        assert '"capped_recall@3": 0.500,' in out
