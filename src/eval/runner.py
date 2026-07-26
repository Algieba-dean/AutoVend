"""
Retrieval evaluation runner.

Runs one or more retrieval systems over the golden set and reports deterministic
ranking metrics. This is where the numbers quoted for the system come from —
nothing here calls an LLM, so a rerun on the same index reproduces them exactly.

Usage:
    python -m src.eval.runner                          # every system
    python -m src.eval.runner --systems hybrid fusion  # A/B two variants
    python -m src.eval.runner --systems filter bm25    # no embedding model needed
    python -m src.eval.runner --markdown report.md     # comparison table
"""

import argparse
import json
import statistics
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Sequence

from src.eval.golden_set import GoldenQuery, load_golden_set
from src.eval.metrics import DEFAULT_KS, aggregate, evaluate_one
from src.eval.systems import ALL_SYSTEMS, build_system
from src.utils.config import PROJECT_ROOT
from src.utils.logger import get_logger

logger = get_logger(__name__)

RESULTS_DIR = PROJECT_ROOT / "evaluation" / "results"

#: Metrics printed in the summary table. The full set is kept in the JSON.
HEADLINE_METRICS = (
    "capped_recall@3",
    "recall@3",
    "precision@3",
    "hit_rate@3",
    "mrr",
    "ndcg@10",
)

#: Retrieval depth. Larger than the largest reported k so every cut-off is
#: computed from one pass.
EVAL_TOP_K = 10


def evaluate_system(
    name: str,
    queries: Sequence[GoldenQuery],
    top_k: int = EVAL_TOP_K,
) -> Dict:
    """Run one system over the golden set and return its full result record."""
    logger.info(f"[eval] building system: {name}")
    system = build_system(name)

    per_query: List[Dict] = []
    latencies: List[float] = []

    for query in queries:
        start = time.perf_counter()
        try:
            retrieved = system(query.query, top_k)
        except Exception as exc:
            logger.error(f"[eval] {name} failed on {query.id} ({query.query!r}): {exc}")
            retrieved = []
        elapsed = time.perf_counter() - start
        latencies.append(elapsed)

        scores = evaluate_one(retrieved, query.relevant_set, DEFAULT_KS)
        per_query.append(
            {
                "id": query.id,
                "query": query.query,
                "tags": query.tags,
                "n_relevant": len(query.relevant_car_models),
                "n_retrieved": len(retrieved),
                "retrieved": retrieved,
                "latency_s": round(elapsed, 4),
                **scores,
            }
        )

    metric_keys = (
        [k for k in per_query[0] if isinstance(per_query[0][k], float) and k != "latency_s"]
        if per_query
        else []
    )

    return {
        "system": name,
        "n_queries": len(queries),
        "overall": aggregate([{k: q[k] for k in metric_keys} for q in per_query]),
        "by_tag": _aggregate_by_tag(per_query, metric_keys),
        "latency": {
            "mean_s": round(statistics.mean(latencies), 4) if latencies else 0.0,
            "median_s": round(statistics.median(latencies), 4) if latencies else 0.0,
            # p95 over ~100 queries; the first call also pays index warm-up.
            "p95_s": round(sorted(latencies)[int(len(latencies) * 0.95)], 4) if latencies else 0.0,
        },
        "per_query": per_query,
    }


def _aggregate_by_tag(per_query: Sequence[Dict], metric_keys: Sequence[str]) -> Dict[str, Dict]:
    """
    Break metrics down by query tag.

    The `broad` slice matters most when reading a report: those queries have
    hundreds of relevant cars, so their recall@3 is structurally near zero and
    drags the overall average down for reasons that have nothing to do with
    retrieval quality.
    """
    tags = sorted({tag for q in per_query for tag in q["tags"]})
    breakdown: Dict[str, Dict] = {}
    for tag in tags:
        subset = [q for q in per_query if tag in q["tags"]]
        breakdown[tag] = {
            "n_queries": len(subset),
            **aggregate([{k: q[k] for k in metric_keys} for q in subset]),
        }

    narrow = [q for q in per_query if "broad" not in q["tags"]]
    if narrow:
        breakdown["_narrow_only"] = {
            "n_queries": len(narrow),
            **aggregate([{k: q[k] for k in metric_keys} for q in narrow]),
        }
    return breakdown


def run(
    systems: Sequence[str],
    golden_path: Optional[Path] = None,
    top_k: int = EVAL_TOP_K,
) -> Dict:
    """Evaluate every named system over the golden set."""
    queries = load_golden_set(golden_path)
    logger.info(f"[eval] golden set: {len(queries)} queries")

    return {
        "n_queries": len(queries),
        "top_k": top_k,
        "systems": [evaluate_system(name, queries, top_k) for name in systems],
    }


# ── reporting ─────────────────────────────────────────────────────────


def format_comparison(report: Dict) -> str:
    """Markdown table comparing the evaluated systems."""
    systems = report["systems"]
    lines = [
        f"# Retrieval evaluation — {report['n_queries']} golden queries",
        "",
        "## Overall (all queries)",
        "",
        "| System | " + " | ".join(HEADLINE_METRICS) + " | mean latency |",
        "|---" * (len(HEADLINE_METRICS) + 2) + "|",
    ]
    for s in systems:
        cells = [f"{s['overall'].get(m, 0.0):.3f}" for m in HEADLINE_METRICS]
        lines.append(
            f"| `{s['system']}` | " + " | ".join(cells) + f" | {s['latency']['mean_s']:.3f}s |"
        )

    narrow = [s for s in systems if "_narrow_only" in s["by_tag"]]
    if narrow:
        lines += [
            "",
            "## Narrow queries only",
            "",
            "Excludes `broad` queries, where recall@3 is capped by |relevant| >> 3.",
            "",
            "| System | " + " | ".join(HEADLINE_METRICS) + " |",
            "|---" * (len(HEADLINE_METRICS) + 1) + "|",
        ]
        for s in narrow:
            slice_ = s["by_tag"]["_narrow_only"]
            cells = [f"{slice_.get(m, 0.0):.3f}" for m in HEADLINE_METRICS]
            lines.append(f"| `{s['system']}` | " + " | ".join(cells) + " |")

    header = " | ".join(f"`{s['system']}`" for s in systems)
    lines += [
        "",
        "## By tag — capped_recall@3",
        "",
        f"| Tag | n | {header} |",
        "|---" * (len(systems) + 2) + "|",
    ]
    all_tags = sorted({t for s in systems for t in s["by_tag"] if not t.startswith("_")})
    for tag in all_tags:
        n = systems[0]["by_tag"].get(tag, {}).get("n_queries", 0)
        cells = [f"{s['by_tag'].get(tag, {}).get('capped_recall@3', 0.0):.3f}" for s in systems]
        lines.append(f"| {tag} | {n} | " + " | ".join(cells) + " |")

    return "\n".join(lines) + "\n"


def save_report(report: Dict, tag: str = "eval") -> Path:
    """Persist the full report as JSON. Filenames are content-stable, not timestamped."""
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    systems = "-".join(s["system"] for s in report["systems"])
    path = RESULTS_DIR / f"{tag}_{systems}.json"
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--systems",
        nargs="+",
        default=list(ALL_SYSTEMS),
        choices=list(ALL_SYSTEMS),
        help="Retrieval systems to evaluate.",
    )
    parser.add_argument("--golden", type=Path, default=None, help="Path to golden_set.jsonl")
    parser.add_argument("--top-k", type=int, default=EVAL_TOP_K)
    parser.add_argument("--markdown", type=Path, default=None, help="Write a comparison table here")
    parser.add_argument("--tag", default="eval", help="Prefix for the results filename")
    args = parser.parse_args(argv)

    report = run(args.systems, args.golden, args.top_k)

    table = format_comparison(report)
    print(table)

    json_path = save_report(report, args.tag)
    print(f"Full report: {json_path}")

    if args.markdown:
        args.markdown.parent.mkdir(parents=True, exist_ok=True)
        args.markdown.write_text(table, encoding="utf-8")
        print(f"Markdown:    {args.markdown}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
