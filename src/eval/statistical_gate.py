"""
src/eval/statistical_gate.py: Statistical confidence gate using Bootstrap CI for non-inferiority checks.

Replaces arbitrary point tolerances with statistically grounded confidence intervals:
A candidate release passes if the lower bound of its bootstrap confidence interval
does not fall below the baseline minus the non-inferiority margin:

    Lower_Bound(candidate) >= Baseline - Margin

Fails (blocks release / CI) if and only if:
    Lower_Bound(candidate) < Baseline - Margin
"""

import argparse
import json
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np

from src.utils.logger import get_logger

logger = get_logger(__name__)

#: Default non-inferiority margin (calibrated for 95% two-sided CI on N=116 golden set queries)
DEFAULT_MARGIN = 0.08

#: Default confidence level (95% two-sided CI -> 2.5% lower / 97.5% upper)
DEFAULT_CI = 0.95

#: Default bootstrap resampling iterations
DEFAULT_N_BOOTSTRAPS = 1000

#: Default baselines calibrated to AutoVend system profiles
DEFAULT_STATISTICAL_BASELINES: Dict[str, Dict[str, float]] = {
    "fusion": {
        "precision@3": 0.756,
        "hit_rate@3": 0.836,
        "mrr": 0.794,
        "ndcg@10": 0.707,
    },
    "hybrid": {
        "precision@3": 0.701,
        "hit_rate@3": 0.793,
        "mrr": 0.755,
        "ndcg@10": 0.716,
    },
    "dense": {
        "precision@3": 0.707,
        "hit_rate@3": 0.845,
        "mrr": 0.782,
        "ndcg@10": 0.708,
    },
    "bm25": {
        "precision@3": 0.707,
        "hit_rate@3": 0.802,
        "mrr": 0.777,
        "ndcg@10": 0.693,
    },
}


def bootstrap_metric_ci(
    scores: Sequence[float],
    n_bootstraps: int = DEFAULT_N_BOOTSTRAPS,
    ci: float = DEFAULT_CI,
    seed: int = 42,
) -> Tuple[float, float, float]:
    """
    Compute empirical bootstrap confidence interval for a metric.

    Returns:
        (lower_bound, mean, upper_bound)
    """
    scores_arr = np.asarray(scores, dtype=float)
    n = len(scores_arr)
    if n == 0:
        return 0.0, 0.0, 0.0
    if n == 1:
        val = float(scores_arr[0])
        return val, val, val

    rng = np.random.default_rng(seed=seed)
    samples = rng.choice(scores_arr, size=(n_bootstraps, n), replace=True)
    bootstrapped_means = np.mean(samples, axis=1)

    alpha = (1.0 - ci) / 2.0 * 100.0
    lower_bound = float(np.percentile(bootstrapped_means, alpha))
    upper_bound = float(np.percentile(bootstrapped_means, 100.0 - alpha))
    mean_val = float(np.mean(scores_arr))

    return lower_bound, mean_val, upper_bound


@dataclass
class NonInferiorityResult:
    """Non-inferiority check result for a single metric."""

    metric_name: str
    sample_size: int
    mean: float
    lower_bound: float
    upper_bound: float
    baseline: float
    margin: float
    threshold: float
    passed: bool
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class StatisticalGateReport:
    """Consolidated statistical gate report across all checked metrics."""

    system: str
    passed: bool
    ci: float
    margin: float
    n_bootstraps: int
    results: Dict[str, NonInferiorityResult] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "system": self.system,
            "passed": self.passed,
            "ci": self.ci,
            "margin": self.margin,
            "n_bootstraps": self.n_bootstraps,
            "results": {k: v.to_dict() for k, v in self.results.items()},
        }


def check_non_inferiority(
    scores: Sequence[float],
    baseline: float,
    margin: float = DEFAULT_MARGIN,
    ci: float = DEFAULT_CI,
    n_bootstraps: int = DEFAULT_N_BOOTSTRAPS,
    metric_name: str = "metric",
    seed: int = 42,
) -> NonInferiorityResult:
    """
    Assert that the candidate scores meet the non-inferiority criterion against baseline.

    Condition:
        lower_bound >= baseline - margin
    """
    lower, mean, upper = bootstrap_metric_ci(scores, n_bootstraps=n_bootstraps, ci=ci, seed=seed)
    threshold = baseline - margin
    passed = lower >= threshold

    return NonInferiorityResult(
        metric_name=metric_name,
        sample_size=len(scores),
        mean=round(mean, 4),
        lower_bound=round(lower, 4),
        upper_bound=round(upper, 4),
        baseline=round(baseline, 4),
        margin=round(margin, 4),
        threshold=round(threshold, 4),
        passed=bool(passed),
    )


def evaluate_statistical_gate(
    per_query_results: Sequence[Dict[str, Any]],
    baselines: Optional[Dict[str, float]] = None,
    system_name: str = "fusion",
    margin: float = DEFAULT_MARGIN,
    ci: float = DEFAULT_CI,
    n_bootstraps: int = DEFAULT_N_BOOTSTRAPS,
    seed: int = 42,
) -> StatisticalGateReport:
    """
    Run stratified statistical non-inferiority gate across narrow and broad query suites.

    - Narrow suite: queries without 'broad' tag -> checks 'narrow_recall@3', 'narrow_mrr'
    - Broad suite: queries with 'broad' tag -> checks 'broad_precision@3', 'broad_ndcg@10'
    """
    expected = baselines or DEFAULT_STATISTICAL_BASELINES.get(
        system_name, DEFAULT_STATISTICAL_BASELINES["fusion"]
    )

    narrow_queries = [q for q in per_query_results if "broad" not in q.get("tags", [])]
    broad_queries = [q for q in per_query_results if "broad" in q.get("tags", [])]

    # If dataset has no broad tags, use all queries for narrow
    if not narrow_queries:
        narrow_queries = list(per_query_results)

    metric_series: Dict[str, List[float]] = {}

    if "narrow_recall@3" in expected:
        metric_series["narrow_recall@3"] = [float(q.get("recall@3", 0.0)) for q in narrow_queries]
    if "narrow_mrr" in expected:
        metric_series["narrow_mrr"] = [float(q.get("mrr", 0.0)) for q in narrow_queries]
    if "broad_precision@3" in expected:
        source = broad_queries if broad_queries else per_query_results
        metric_series["broad_precision@3"] = [float(q.get("precision@3", 0.0)) for q in source]
    if "broad_ndcg@10" in expected:
        source = broad_queries if broad_queries else per_query_results
        metric_series["broad_ndcg@10"] = [float(q.get("ndcg@10", 0.0)) for q in source]

    # Support generic metrics passed in expected
    for m, baseline_val in expected.items():
        if m not in metric_series:
            metric_series[m] = [float(q.get(m, 0.0)) for q in per_query_results]

    results: Dict[str, NonInferiorityResult] = {}
    all_passed = True

    for metric_name, scores in metric_series.items():
        baseline_val = expected[metric_name]
        res = check_non_inferiority(
            scores=scores,
            baseline=baseline_val,
            margin=margin,
            ci=ci,
            n_bootstraps=n_bootstraps,
            metric_name=metric_name,
            seed=seed,
        )
        results[metric_name] = res
        if not res.passed:
            all_passed = False

    return StatisticalGateReport(
        system=system_name,
        passed=all_passed,
        ci=ci,
        margin=margin,
        n_bootstraps=n_bootstraps,
        results=results,
    )


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--results",
        type=Path,
        default=None,
        help="Path to runner results JSON containing per_query records.",
    )
    parser.add_argument(
        "--system",
        default="fusion",
        help="Retrieval system name if running evaluation live.",
    )
    parser.add_argument(
        "--margin",
        type=float,
        default=DEFAULT_MARGIN,
        help="Non-inferiority tolerance margin.",
    )
    parser.add_argument(
        "--ci",
        type=float,
        default=DEFAULT_CI,
        help="Confidence interval level (e.g. 0.95).",
    )
    parser.add_argument(
        "--n-bootstraps",
        type=int,
        default=DEFAULT_N_BOOTSTRAPS,
        help="Number of bootstrap resamples.",
    )
    parser.add_argument(
        "--json-out",
        type=Path,
        default=None,
        help="Path to write structured JSON gate output.",
    )
    args = parser.parse_args(argv)

    if args.results is not None:
        if not args.results.exists():
            print(f"Error: results file not found at {args.results}", file=sys.stderr)
            return 1
        data = json.loads(args.results.read_text(encoding="utf-8"))
        if "systems" in data:
            match = next(
                (s for s in data["systems"] if s["system"] == args.system), data["systems"][0]
            )
            per_query = match.get("per_query", [])
        else:
            per_query = data.get("per_query", [])
    else:
        # Load from golden set and run system evaluation
        from src.eval.golden_set import load_golden_set
        from src.eval.runner import evaluate_system

        queries = load_golden_set()
        eval_report = evaluate_system(args.system, queries)
        per_query = eval_report.get("per_query", [])

    report = evaluate_statistical_gate(
        per_query_results=per_query,
        system_name=args.system,
        margin=args.margin,
        ci=args.ci,
        n_bootstraps=args.n_bootstraps,
    )

    print(
        f"\n📊 Statistical Confidence Gate (System: {report.system}, CI: {report.ci:.0%}, Margin: {report.margin:.3f})"
    )
    print("=" * 80)
    print(f"{'Metric':<22} {'Mean':<8} {'95% CI':<18} {'Baseline':<10} {'Floor':<10} {'Status'}")
    print("-" * 80)

    for name, r in report.results.items():
        ci_str = f"[{r.lower_bound:.3f}, {r.upper_bound:.3f}]"
        status = "✅ PASS" if r.passed else "❌ FAIL"
        print(
            f"{name:<22} {r.mean:<8.3f} {ci_str:<18} {r.baseline:<10.3f} {r.threshold:<10.3f} {status}"
        )
    print("=" * 80)

    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(
            json.dumps(report.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"Output saved to {args.json_out}")

    if not report.passed:
        print(
            "\n❌ CI Gate Blocked: Metric CI lower bound is below non-inferiority margin!",
            file=sys.stderr,
        )
        return 1

    print("\n✅ Statistical confidence gate passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
