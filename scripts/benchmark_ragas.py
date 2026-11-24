"""
RAGAS End-to-End Evaluation Benchmark (`scripts/benchmark_ragas.py`).

Wraps `src/eval/ragas_eval.py` with:
- Default `deepseek-chat` judge selection when `DEEPSEEK_API_KEY` is configured
- Bootstrap 95% confidence intervals via `src.eval.statistical_gate.bootstrap_metric_ci`
- Offline `--mock` mode for deterministic verification without live LLM APIs or `ragas` installed

Usage:
    python scripts/benchmark_ragas.py --sample 10 --system fusion
    python scripts/benchmark_ragas.py --mock --sample 5
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, Optional, Sequence

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.eval.ragas_eval import (  # noqa: E402
    build_samples,
    resolve_judge,
    run_ragas,
    summarize,
)
from src.eval.runner import RESULTS_DIR  # noqa: E402
from src.eval.statistical_gate import bootstrap_metric_ci  # noqa: E402


def _run_mock_benchmark(sample_limit: int = 5, system_name: str = "fusion") -> Dict[str, Any]:
    """Deterministic offline dry-run verifying sample construction & bootstrap CI reporting."""
    from src.eval.golden_set import load_golden_set

    queries = load_golden_set()[:sample_limit]
    per_sample_faithfulness = [round(0.88 + 0.03 * (i % 3), 4) for i in range(len(queries))]
    per_sample_relevancy = [round(0.84 + 0.03 * (i % 3), 4) for i in range(len(queries))]
    per_sample_recall = [round(0.80 + 0.04 * (i % 3), 4) for i in range(len(queries))]

    scores = {}
    for name, vals in (
        ("faithfulness", per_sample_faithfulness),
        ("answer_relevancy", per_sample_relevancy),
        ("context_recall", per_sample_recall),
    ):
        ci_lo, mean_val, ci_hi = bootstrap_metric_ci(vals)
        scores[name] = {
            "score": round(mean_val, 4),
            "ci_95": [round(ci_lo, 4), round(ci_hi, 4)],
            "n_scored": len(vals),
            "n_failed": 0,
        }

    return {
        "mode": "mock",
        "system": system_name,
        "judge_model": "mock-judge",
        "generator_model": "mock-generator",
        "n_samples": len(queries),
        "scores": scores,
        "query_ids": [q.id for q in queries],
    }


def run_benchmark(
    sample_limit: int = 10,
    system_name: str = "fusion",
    preferred_judge: Optional[str] = "deepseek",
    use_mock: bool = False,
    out_path: Optional[Path] = None,
) -> Dict[str, Any]:
    if use_mock:
        report = _run_mock_benchmark(sample_limit=sample_limit, system_name=system_name)
    else:
        try:
            judge_config = resolve_judge(preferred_judge)
        except SystemExit:
            judge_config = resolve_judge(None)

        samples = build_samples(judge_config, system_name=system_name, limit=sample_limit)
        if not samples:
            raise RuntimeError("No RAGAS samples could be built — check index & golden set.")

        result = run_ragas(samples, judge_config)
        scores = summarize(result)
        report = {
            "mode": "live",
            "system": system_name,
            "judge_model": judge_config["model"],
            "generator_model": judge_config["model"],
            "n_samples": len(samples),
            "scores": scores,
            "query_ids": [s["_id"] for s in samples],
        }

    target = out_path or (RESULTS_DIR / f"ragas_benchmark_{system_name}.json")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Run RAGAS evaluation benchmark.")
    parser.add_argument("--sample", type=int, default=10, help="Number of golden queries to evaluate")
    parser.add_argument("--system", default="fusion", help="Retrieval system under evaluation")
    parser.add_argument("--judge", default="deepseek", help="Preferred judge model substring")
    parser.add_argument("--mock", action="store_true", help="Run offline deterministic mock benchmark")
    parser.add_argument("--out", type=Path, default=None, help="Output JSON report path")
    args = parser.parse_args(argv)

    report = run_benchmark(
        sample_limit=args.sample,
        system_name=args.system,
        preferred_judge=args.judge,
        use_mock=args.mock,
        out_path=args.out,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
