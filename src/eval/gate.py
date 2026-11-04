"""
CI evaluation gate.

Blocks a release when retrieval quality regresses below a recorded baseline.
Everything here is deterministic — no LLM, no sampling — so a red gate means
the index or the retrieval code changed, never that a judge model had an off
day. LLM-judged metrics live in `src/eval/ragas_eval.py` and deliberately do
not gate.

Baselines are **measured, not aspirational.** Each number below was produced by
`python -m src.eval.runner` against the 116-query golden set and then relaxed by
`TOLERANCE` so ordinary noise (a rebuilt index, a tie broken differently) does
not fail the build. Raising a baseline after a genuine improvement is expected;
lowering one to make CI green is how a gate becomes decoration.

Usage:
    python -m src.eval.gate                    # gate the production path
    python -m src.eval.gate --system bm25      # gate a variant
    python -m src.eval.gate --update-baseline  # print refreshed values
"""

import argparse
import sys
from typing import Dict, Optional, Sequence

from src.eval.golden_set import load_golden_set
from src.eval.runner import evaluate_system
from src.utils.logger import get_logger

logger = get_logger(__name__)

#: Slack allowed below the recorded baseline before the gate fails.
#: 2 points absolute — roughly one query out of 116 flipping on each metric.
TOLERANCE = 0.02

#: Measured on the 116-query golden set (`evaluation/results/ab_*.json`).
#: Recorded to 3 decimals; the gate compares against value - TOLERANCE.
BASELINES: Dict[str, Dict[str, float]] = {
    "fusion": {
        "capped_recall@3": 0.336,
        "hit_rate@3": 0.388,
        "mrr": 0.367,
        "ndcg@10": 0.311,
    },
    "hybrid": {
        "capped_recall@3": 0.230,
        "hit_rate@3": 0.284,
        "mrr": 0.249,
        "ndcg@10": 0.223,
    },
    "dense": {
        "capped_recall@3": 0.322,
        "hit_rate@3": 0.388,
        "mrr": 0.363,
        "ndcg@10": 0.299,
    },
    "bm25": {
        "capped_recall@3": 0.305,
        "hit_rate@3": 0.371,
        "mrr": 0.357,
        "ndcg@10": 0.280,
    },
    "filter": {
        "capped_recall@3": 0.210,
        "hit_rate@3": 0.250,
        "mrr": 0.230,
        "ndcg@10": 0.200,
    },
}

#: The variant actually served to users, and therefore the one CI gates.
PRODUCTION_SYSTEM = "fusion"


class GateFailure(Exception):
    """Raised when a metric falls below its baseline."""


def check(
    system: str = PRODUCTION_SYSTEM,
    tolerance: float = TOLERANCE,
    baselines: Optional[Dict[str, float]] = None,
) -> Dict[str, Dict[str, float]]:
    """
    Evaluate `system` and compare every gated metric against its baseline.

    Returns:
        {metric: {"measured": .., "baseline": .., "floor": .., "delta": ..}}

    Raises:
        GateFailure: if any metric is below baseline - tolerance.
        KeyError: if the system has no recorded baseline.
    """
    expected = baselines if baselines is not None else BASELINES[system]

    queries = load_golden_set()
    report = evaluate_system(system, queries)
    measured = report["overall"]

    comparison: Dict[str, Dict[str, float]] = {}
    failures = []
    for metric, baseline in expected.items():
        value = measured.get(metric, 0.0)
        floor = baseline - tolerance
        comparison[metric] = {
            "measured": round(value, 4),
            "baseline": baseline,
            "floor": round(floor, 4),
            "delta": round(value - baseline, 4),
        }
        if value < floor:
            failures.append(f"{metric}: {value:.4f} < {floor:.4f} (baseline {baseline:.3f})")

    if failures:
        raise GateFailure(
            f"Retrieval quality regressed on '{system}' over "
            f"{len(queries)} golden queries:\n  " + "\n  ".join(failures)
        )

    return comparison


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--system", default=PRODUCTION_SYSTEM, choices=sorted(BASELINES))
    parser.add_argument("--tolerance", type=float, default=TOLERANCE)
    parser.add_argument(
        "--update-baseline",
        action="store_true",
        help="Measure and print refreshed baselines instead of gating.",
    )
    args = parser.parse_args(argv)

    if args.update_baseline:
        queries = load_golden_set()
        report = evaluate_system(args.system, queries)
        overall = report["overall"]
        print(f'    "{args.system}": {{')
        for metric in BASELINES[args.system]:
            print(f'        "{metric}": {overall.get(metric, 0.0):.3f},')
        print("    },")
        return 0

    try:
        comparison = check(args.system, args.tolerance)
    except GateFailure as exc:
        print(f"FAIL  {exc}", file=sys.stderr)
        return 1

    print(f"PASS  retrieval gate — system '{args.system}'")
    width = max(len(m) for m in comparison)
    for metric, row in comparison.items():
        sign = "+" if row["delta"] >= 0 else ""
        print(
            f"  {metric:<{width}}  {row['measured']:.4f}  "
            f"(baseline {row['baseline']:.3f}, {sign}{row['delta']:.4f})"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
