"""
Per-call LLM telemetry.

Routing traffic between a local model and a cloud API is only worth doing if
the split can be shown to pay off, so every call records where it went, how
long the first token took, and what it would have cost. Without this the
routing policy is an assertion; with it, it is a measurement.

Deliberately process-local and in-memory: this is a development and evaluation
instrument, not a metrics backend. Nothing here writes to disk or blocks a
request.
"""

import statistics
import threading
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional


class Route(str, Enum):
    """Where a call was served."""

    LOCAL = "local"
    CLOUD = "cloud"
    MOCK = "mock"


#: USD per 1M tokens. Local inference has no per-token price — the GPU is paid
#: for whether or not it is busy — so it is priced at zero and the saving is
#: read as "cloud tokens not spent".
PRICING_USD_PER_MTOK: Dict[str, Dict[str, float]] = {
    # Groq on-demand pricing for Llama 3.3 70B, Jan 2026.
    "cloud": {"input": 0.59, "output": 0.79},
    "local": {"input": 0.0, "output": 0.0},
    "mock": {"input": 0.0, "output": 0.0},
}


@dataclass
class CallRecord:
    """One LLM call."""

    task: str
    route: Route
    model: str
    latency_s: float
    ttft_s: Optional[float] = None
    prompt_tokens: int = 0
    completion_tokens: int = 0
    ok: bool = True
    error: str = ""

    @property
    def cost_usd(self) -> float:
        price = PRICING_USD_PER_MTOK.get(self.route.value, PRICING_USD_PER_MTOK["mock"])
        return (
            self.prompt_tokens * price["input"] + self.completion_tokens * price["output"]
        ) / 1_000_000


@dataclass
class TelemetryCollector:
    """Thread-safe in-memory record of LLM calls."""

    records: List[CallRecord] = field(default_factory=list)
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def record(self, call: CallRecord) -> None:
        with self._lock:
            self.records.append(call)

    def reset(self) -> None:
        with self._lock:
            self.records.clear()

    @contextmanager
    def measure(self, task: str, route: Route, model: str):
        """
        Time a call and record it, whether it succeeds or raises.

        Yields a mutable record so the caller can fill in token counts and TTFT
        once the response is in hand.
        """
        started = time.perf_counter()
        call = CallRecord(task=task, route=route, model=model, latency_s=0.0)
        try:
            yield call
        except Exception as exc:
            call.ok = False
            call.error = f"{type(exc).__name__}: {exc}"
            raise
        finally:
            call.latency_s = time.perf_counter() - started
            self.record(call)

    # ── reporting ─────────────────────────────────────────────────────

    def summary(self) -> Dict:
        """Aggregate overall, by route, and by task."""
        with self._lock:
            records = list(self.records)

        if not records:
            return {"n_calls": 0, "by_route": {}, "by_task": {}}

        return {
            "n_calls": len(records),
            "overall": _aggregate(records),
            "by_route": {
                route.value: _aggregate([r for r in records if r.route is route])
                for route in Route
                if any(r.route is route for r in records)
            },
            "by_task": {
                task: _aggregate([r for r in records if r.task == task])
                for task in sorted({r.task for r in records})
            },
            "cost": self.cost_breakdown(records),
        }

    def cost_breakdown(self, records: Optional[List[CallRecord]] = None) -> Dict:
        """
        Actual spend versus the all-cloud counterfactual.

        The saving is what the locally-served calls *would* have cost at cloud
        rates — the honest way to state it, since the GPU's own cost is fixed
        and unrelated to how many calls it serves.
        """
        if records is None:
            with self._lock:
                records = list(self.records)

        actual = sum(r.cost_usd for r in records)
        cloud_price = PRICING_USD_PER_MTOK["cloud"]
        all_cloud = sum(
            (r.prompt_tokens * cloud_price["input"] + r.completion_tokens * cloud_price["output"])
            / 1_000_000
            for r in records
        )
        saved = all_cloud - actual
        return {
            "actual_usd": round(actual, 6),
            "all_cloud_usd": round(all_cloud, 6),
            "saved_usd": round(saved, 6),
            "saved_pct": round(100 * saved / all_cloud, 2) if all_cloud else 0.0,
        }


def _aggregate(records: List[CallRecord]) -> Dict:
    if not records:
        return {}
    latencies = sorted(r.latency_s for r in records)
    ttfts = sorted(r.ttft_s for r in records if r.ttft_s is not None)

    stats = {
        "n_calls": len(records),
        "n_failed": sum(1 for r in records if not r.ok),
        "latency_mean_s": round(statistics.mean(latencies), 4),
        "latency_p50_s": round(_percentile(latencies, 50), 4),
        "latency_p95_s": round(_percentile(latencies, 95), 4),
        "latency_p99_s": round(_percentile(latencies, 99), 4),
        "prompt_tokens": sum(r.prompt_tokens for r in records),
        "completion_tokens": sum(r.completion_tokens for r in records),
    }
    if ttfts:
        stats.update(
            {
                "ttft_mean_s": round(statistics.mean(ttfts), 4),
                "ttft_p50_s": round(_percentile(ttfts, 50), 4),
                "ttft_p95_s": round(_percentile(ttfts, 95), 4),
                "ttft_p99_s": round(_percentile(ttfts, 99), 4),
            }
        )
    return stats


def _percentile(sorted_values: List[float], pct: float) -> float:
    """
    Nearest-rank percentile.

    With a handful of samples p99 is simply the maximum — stated plainly rather
    than interpolated into a number that looks more precise than the data is.
    """
    if not sorted_values:
        return 0.0
    index = min(len(sorted_values) - 1, int(round(pct / 100 * len(sorted_values) + 0.5)) - 1)
    return sorted_values[max(0, index)]


#: Process-wide collector. Tests and evaluation runs call reset() first.
telemetry = TelemetryCollector()
