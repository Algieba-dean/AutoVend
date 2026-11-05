"""
Tests for statistical confidence gate (Bootstrap CI & non-inferiority) and metrics contract.
"""

import json

import pytest

from src.eval.metrics_contract import (
    DriftContract,
    MetricsContract,
    RetrievalContract,
    diff_metrics_contracts,
    format_diff_markdown,
)
from src.eval.statistical_gate import (
    NonInferiorityResult,
    StatisticalGateReport,
    bootstrap_metric_ci,
    check_non_inferiority,
    evaluate_statistical_gate,
)


class TestBootstrapCI:
    def test_empty_list_returns_zeros(self):
        lower, mean, upper = bootstrap_metric_ci([])
        assert lower == 0.0
        assert mean == 0.0
        assert upper == 0.0

    def test_single_element_returns_identical_tuple(self):
        lower, mean, upper = bootstrap_metric_ci([0.75])
        assert lower == 0.75
        assert mean == 0.75
        assert upper == 0.75

    def test_constant_distribution_bounds_match_mean(self):
        lower, mean, upper = bootstrap_metric_ci([0.8] * 50)
        assert lower == pytest.approx(0.8)
        assert mean == pytest.approx(0.8)
        assert upper == pytest.approx(0.8)

    def test_lower_mean_upper_ordering(self):
        scores = [0.1, 0.4, 0.5, 0.7, 0.9, 0.8, 0.6, 0.75]
        lower, mean, upper = bootstrap_metric_ci(scores, n_bootstraps=500, ci=0.95, seed=42)
        assert lower <= mean <= upper
        assert 0.0 <= lower <= 1.0
        assert 0.0 <= upper <= 1.0

    def test_reproducible_with_seed(self):
        scores = [0.2, 0.5, 0.8, 0.9, 0.7]
        r1 = bootstrap_metric_ci(scores, n_bootstraps=100, seed=123)
        r2 = bootstrap_metric_ci(scores, n_bootstraps=100, seed=123)
        assert r1 == r2


class TestNonInferiorityCheck:
    def test_passes_when_distribution_matches_baseline(self):
        # Baseline = 0.8, scores clustered around 0.82
        scores = [0.80, 0.82, 0.85, 0.81, 0.79, 0.83] * 10
        result = check_non_inferiority(
            scores=scores, baseline=0.80, margin=0.03, metric_name="narrow_recall@3"
        )
        assert isinstance(result, NonInferiorityResult)
        assert result.passed is True
        assert result.metric_name == "narrow_recall@3"
        assert result.lower_bound >= result.threshold

    def test_passes_within_margin(self):
        # Baseline = 0.85, scores around 0.84, margin = 0.05 (threshold = 0.80)
        scores = [0.83, 0.84, 0.85, 0.84, 0.82] * 10
        result = check_non_inferiority(
            scores=scores, baseline=0.85, margin=0.05, metric_name="recall@3"
        )
        assert result.passed is True

    def test_fails_when_statistically_degraded_beyond_margin(self):
        # Baseline = 0.90, margin = 0.03 (threshold = 0.87), scores around 0.70
        scores = [0.68, 0.70, 0.72, 0.69, 0.71] * 10
        result = check_non_inferiority(
            scores=scores, baseline=0.90, margin=0.03, metric_name="recall@3"
        )
        assert result.passed is False
        assert result.lower_bound < result.threshold


class TestEvaluateStatisticalGate:
    def test_evaluates_stratified_suites(self):
        per_query = [
            {"id": "q1", "tags": ["narrow"], "recall@3": 0.85, "mrr": 0.90, "precision@3": 0.80},
            {"id": "q2", "tags": ["narrow"], "recall@3": 0.80, "mrr": 0.85, "precision@3": 0.75},
            {"id": "q3", "tags": ["broad"], "recall@3": 0.05, "precision@3": 0.95, "ndcg@10": 0.88},
            {"id": "q4", "tags": ["broad"], "recall@3": 0.02, "precision@3": 0.90, "ndcg@10": 0.85},
        ]
        baselines = {
            "narrow_recall@3": 0.75,
            "narrow_mrr": 0.80,
            "broad_precision@3": 0.85,
            "broad_ndcg@10": 0.80,
        }

        report = evaluate_statistical_gate(
            per_query_results=per_query,
            baselines=baselines,
            system_name="fusion",
            margin=0.05,
            n_bootstraps=200,
        )

        assert isinstance(report, StatisticalGateReport)
        assert report.passed is True
        assert "narrow_recall@3" in report.results
        assert "broad_precision@3" in report.results
        d = report.to_dict()
        assert d["system"] == "fusion"
        assert d["passed"] is True


class TestMetricsContract:
    def test_contract_serialization(self, tmp_path):
        contract = MetricsContract(
            commit="abcdef1",
            retrieval=RetrievalContract(
                p50_latency_ms=12.5,
                p99_latency_ms=35.0,
                narrow_recall_at_3=0.88,
                broad_precision_at_3=0.76,
                mrr=0.82,
            ),
            drift=DriftContract(
                overall_level="normal",
                embedding_distance=0.015,
            ),
        )
        d = contract.to_dict()
        assert d["schema_version"] == "v1.0"
        assert d["commit"] == "abcdef1"
        assert d["retrieval"]["narrow_recall_at_3"] == 0.88
        assert d["drift"]["overall_level"] == "normal"

        out_file = tmp_path / "contract.json"
        contract.write_json(out_file)
        assert out_file.exists()
        loaded = json.loads(out_file.read_text(encoding="utf-8"))
        assert loaded["commit"] == "abcdef1"

    def test_diff_metrics_contracts_and_markdown(self):
        baseline = {
            "commit": "base001",
            "retrieval": {
                "p50_latency_ms": 20.0,
                "narrow_recall_at_3": 0.80,
                "broad_precision_at_3": 0.70,
                "mrr": 0.75,
            },
        }
        current = {
            "commit": "curr002",
            "retrieval": {
                "p50_latency_ms": 15.0,  # Improved (lower)
                "narrow_recall_at_3": 0.85,  # Improved (higher)
                "broad_precision_at_3": 0.65,  # Regressed (lower)
                "mrr": 0.75,  # Stable
            },
        }

        diff = diff_metrics_contracts(current, baseline)
        assert diff["current_commit"] == "curr002"
        assert diff["baseline_commit"] == "base001"
        assert diff["deltas"]["narrow_recall_at_3"]["delta"] == 0.05
        assert diff["deltas"]["p50_latency_ms"]["delta"] == -5.0

        md = format_diff_markdown(diff)
        assert "## 📊 MLOps Automated PR Quality & Performance Diff" in md
        assert "🟢 Improved" in md
        assert "🔴 Regressed" in md
        assert "⚪ Stable" in md

    def test_diff_metrics_contracts_multi_section(self):
        baseline = {
            "commit": "base001",
            "qps": 20.0,
            "drift": {"embedding_distance": 0.010},
            "performance": {"peak_memory_mb": 1500.0},
            "retrieval": {"mrr": 0.75},
        }
        current = {
            "commit": "curr002",
            "qps": 25.0,
            "drift": {"embedding_distance": 0.012},
            "performance": {"peak_memory_mb": 1400.0},
            "retrieval": {"mrr": 0.78},
        }
        diff = diff_metrics_contracts(current, baseline)
        assert "qps" in diff["deltas"]
        assert diff["deltas"]["qps"]["delta"] == 5.0
        assert "drift_embedding_distance" in diff["deltas"]
        assert "peak_memory_mb" in diff["deltas"]
        assert diff["deltas"]["peak_memory_mb"]["delta"] == -100.0


class TestStatisticalGateMain:
    def test_main_with_valid_results_file(self, tmp_path):
        results_file = tmp_path / "results.json"
        data = {
            "systems": [
                {
                    "system": "fusion",
                    "per_query": [
                        {
                            "id": f"q{i}",
                            "precision@3": 0.76,
                            "hit_rate@3": 0.84,
                            "mrr": 0.80,
                            "ndcg@10": 0.71,
                        }
                        for i in range(100)
                    ],
                }
            ]
        }
        results_file.write_text(json.dumps(data), encoding="utf-8")
        out_file = tmp_path / "gate_out.json"

        from src.eval import statistical_gate

        ret = statistical_gate.main(
            ["--results", str(results_file), "--system", "fusion", "--json-out", str(out_file)]
        )
        assert ret == 0
        assert out_file.exists()
        out_data = json.loads(out_file.read_text(encoding="utf-8"))
        assert out_data["passed"] is True

    def test_main_with_missing_results_file_fails(self, tmp_path):
        from src.eval import statistical_gate

        ret = statistical_gate.main(["--results", str(tmp_path / "nonexistent.json")])
        assert ret == 1
