"""
src/eval/metrics_contract.py: Structured Metrics JSON Contract and automated Diff Generator.

Implements the standard Metrics Contract schema specified in Architecture RFC-MLOps:
{
  "schema_version": "v1.0",
  "timestamp": 1730811000,
  "commit": "6233440",
  "retrieval": {
    "p50_latency_ms": 14.2,
    "p99_latency_ms": 48.7,
    "narrow_recall_at_3": 0.884,
    "broad_precision_at_3": 0.762,
    "mrr": 0.812
  },
  "drift": {
    "overall_level": "normal",
    "embedding_distance": 0.012
  }
}
"""

import argparse
import json
import os
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional, Sequence

from src.utils.logger import get_logger

logger = get_logger(__name__)

SCHEMA_VERSION = "v1.0"


def get_current_git_commit() -> str:
    """Safely get current commit SHA or environment override."""
    commit = os.environ.get("GITHUB_SHA")
    if commit:
        return commit[:7]
    try:
        res = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            check=False,
        )
        if res.returncode == 0 and res.stdout.strip():
            return res.stdout.strip()
    except Exception:
        pass
    return "unknown"


@dataclass
class RetrievalContract:
    p50_latency_ms: float = 0.0
    p99_latency_ms: float = 0.0
    narrow_recall_at_3: float = 0.0
    broad_precision_at_3: float = 0.0
    mrr: float = 0.0
    extra: Dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        d = {
            "p50_latency_ms": round(self.p50_latency_ms, 2),
            "p99_latency_ms": round(self.p99_latency_ms, 2),
            "narrow_recall_at_3": round(self.narrow_recall_at_3, 4),
            "broad_precision_at_3": round(self.broad_precision_at_3, 4),
            "mrr": round(self.mrr, 4),
        }
        if self.extra:
            d["extra"] = self.extra
        return d


@dataclass
class DriftContract:
    overall_level: str = "normal"
    embedding_distance: float = 0.0
    extra: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "overall_level": self.overall_level,
            "embedding_distance": round(self.embedding_distance, 4),
            **self.extra,
        }


@dataclass
class MetricsContract:
    schema_version: str = SCHEMA_VERSION
    timestamp: int = field(default_factory=lambda: int(time.time()))
    commit: str = field(default_factory=get_current_git_commit)
    retrieval: RetrievalContract = field(default_factory=RetrievalContract)
    drift: DriftContract = field(default_factory=DriftContract)
    performance: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        d = {
            "schema_version": self.schema_version,
            "timestamp": self.timestamp,
            "commit": self.commit,
            "retrieval": self.retrieval.to_dict(),
            "drift": self.drift.to_dict(),
        }
        if self.performance:
            d["performance"] = self.performance
        return d

    def write_json(self, path: Path) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(self.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return path


def build_metrics_contract_from_runner(report: Dict[str, Any]) -> MetricsContract:
    """Extract standard metrics contract from runner.py evaluation report."""
    systems = report.get("systems", [])
    prod = next((s for s in systems if s["system"] == "fusion"), systems[0] if systems else {})

    overall = prod.get("overall", {})
    by_tag = prod.get("by_tag", {})
    latencies = prod.get("latency", {})

    narrow_slice = by_tag.get("_narrow_only", overall)
    broad_slice = by_tag.get("broad", overall)

    # Convert latencies in seconds to ms
    median_s = latencies.get("median_s", 0.0)
    p95_s = latencies.get("p95_s", 0.0)

    retrieval = RetrievalContract(
        p50_latency_ms=median_s * 1000.0,
        p99_latency_ms=p95_s * 1000.0,  # Proxy or p95
        narrow_recall_at_3=narrow_slice.get("recall@3", overall.get("recall@3", 0.0)),
        broad_precision_at_3=broad_slice.get("precision@3", overall.get("precision@3", 0.0)),
        mrr=overall.get("mrr", 0.0),
    )

    # Optional drift info
    drift = DriftContract()
    try:
        from src.mlops import semantic_drift_detector

        rep = semantic_drift_detector.generate_drift_report()
        drift.overall_level = rep.overall_level.value
        if rep.embedding_drift:
            drift.embedding_distance = rep.embedding_drift.centroid_distance
    except Exception:
        pass

    return MetricsContract(
        retrieval=retrieval,
        drift=drift,
    )


def _collect_numeric_metrics(contract: Dict[str, Any]) -> Dict[str, float]:
    """Extract flat mapping of all numeric metric fields across sections."""
    metrics: Dict[str, float] = {}

    for k, v in contract.get("retrieval", {}).items():
        if k != "extra" and isinstance(v, (int, float)):
            metrics[k] = float(v)

    for k, v in contract.get("performance", {}).items():
        if isinstance(v, (int, float)):
            metrics[k] = float(v)

    for k, v in contract.get("drift", {}).items():
        if k != "extra" and isinstance(v, (int, float)):
            metrics[f"drift_{k}"] = float(v)

    ignore_keys = {"schema_version", "timestamp", "commit", "retrieval", "performance", "drift"}
    for k, v in contract.items():
        if k not in ignore_keys and isinstance(v, (int, float)) and k not in metrics:
            metrics[k] = float(v)

    return metrics


def diff_metrics_contracts(current: Dict[str, Any], baseline: Dict[str, Any]) -> Dict[str, Any]:
    """Compute numerical delta between current metrics and baseline metrics."""
    diff_report: Dict[str, Any] = {
        "current_commit": current.get("commit", "unknown"),
        "baseline_commit": baseline.get("commit", "baseline"),
        "deltas": {},
    }

    curr_metrics = _collect_numeric_metrics(current)
    base_metrics = _collect_numeric_metrics(baseline)
    all_keys = sorted(set(curr_metrics) | set(base_metrics))

    for k in all_keys:
        c_val = curr_metrics.get(k)
        b_val = base_metrics.get(k)
        if c_val is not None and b_val is not None:
            delta = c_val - b_val
            pct = (delta / b_val * 100.0) if b_val != 0 else 0.0
            diff_report["deltas"][k] = {
                "current": round(c_val, 4),
                "baseline": round(b_val, 4),
                "delta": round(delta, 4),
                "pct_change": round(pct, 2),
            }

    return diff_report


def format_diff_markdown(diff: Dict[str, Any]) -> str:
    """Format numerical diff report into GitHub Actions PR Summary Markdown table."""
    c_sha = diff.get("current_commit", "unknown")
    b_sha = diff.get("baseline_commit", "baseline")

    lines = [
        "## 📊 MLOps Automated PR Quality & Performance Diff",
        f"**Candidate Commit:** `{c_sha}` | **Baseline Commit:** `{b_sha}`",
        "",
        "| Metric | Current | Baseline | Delta (Δ) | % Change | Status |",
        "|---|---|---|---|---|:---:|",
    ]

    for k, row in diff.get("deltas", {}).items():
        curr = row["current"]
        base = row["baseline"]
        delta = row["delta"]
        pct = row["pct_change"]

        # Latency / Memory / Drift: lower is better; Recall/Precision/MRR/QPS/Accuracy: higher is better
        is_lower_better = "latency" in k or "time" in k or "memory" in k or "drift" in k
        if is_lower_better:
            improved = delta < 0
            regressed = delta > 0 and pct > 10.0
        else:
            improved = delta > 0
            regressed = delta < -0.02

        if improved:
            status = "🟢 Improved"
        elif regressed:
            status = "🔴 Regressed"
        else:
            status = "⚪ Stable"

        delta_sign = "+" if delta > 0 else ""
        lines.append(
            f"| `{k}` | **{curr}** | {base} | {delta_sign}{delta} | {delta_sign}{pct}% | {status} |"
        )

    lines.append("")
    return "\n".join(lines)


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="cmd")

    diff_parser = subparsers.add_parser("diff", help="Diff current against baseline contract")
    diff_parser.add_argument("current", type=Path, help="Path to current metrics contract JSON")
    diff_parser.add_argument("baseline", type=Path, help="Path to baseline metrics contract JSON")
    diff_parser.add_argument(
        "--markdown", type=Path, default=None, help="Output markdown diff path"
    )

    args = parser.parse_args(argv)

    if args.cmd == "diff":
        curr = json.loads(args.current.read_text(encoding="utf-8"))
        base = json.loads(args.baseline.read_text(encoding="utf-8"))
        diff = diff_metrics_contracts(curr, base)
        md = format_diff_markdown(diff)
        print(md)
        if args.markdown:
            args.markdown.parent.mkdir(parents=True, exist_ok=True)
            args.markdown.write_text(md, encoding="utf-8")
        return 0

    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
