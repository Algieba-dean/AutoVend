"""
Serial vs. concurrent evaluation, measured on the same tasks.

Run:
    uv run python -m src.eval.queue_bench --pairs 6

Both halves judge identical cases with an identical judge against the same
provider, minutes apart, so the wall-clock difference is attributable to the
queue rather than to case difficulty or provider weather. The serial half runs
first, which is the pessimistic ordering — a warm provider would flatter the
concurrent half.
"""

import argparse
import json
import math
from pathlib import Path
from typing import Any, Dict

from src.eval.async_runner import judge_tasks, run_queue_sync, run_serial
from src.eval.judge import JudgeMode, StructuredJudge
from src.eval.judge_ab import build_cases
from src.eval.ragas_eval import resolve_judge
from src.eval.rate_limit import RateLimits
from src.llm.factory import LLMFactory

RESULTS_DIR = Path("evaluation/results")


def _bench(judge, cases, limits: RateLimits, serial_first: bool = True) -> Dict[str, Any]:
    def run_serial_half():
        r = run_serial(judge_tasks(judge, cases))
        print(
            f"  serial:     {r.wall_seconds:6.1f}s  ({r.n_ok}/{r.n_tasks} ok, "
            f"{r.mean_latency:.1f}s/call)"
        )
        return r

    def run_concurrent_half():
        r = run_queue_sync(judge_tasks(judge, cases), limits=limits)
        print(
            f"  concurrent: {r.wall_seconds:6.1f}s  ({r.n_ok}/{r.n_tasks} ok, "
            f"{r.mean_latency:.1f}s/call, "
            f"{r.limiter.get('retries', 0)} retries, "
            f"{r.limiter.get('wait_seconds', 0)}s throttled)"
        )
        return r

    # Order is counter-balanced across trials. Whichever half runs first pays
    # connection setup and a cold provider cache, so a fixed order biases the
    # comparison in a direction that does not cancel out.
    if serial_first:
        serial, concurrent = run_serial_half(), run_concurrent_half()
    else:
        concurrent, serial = run_concurrent_half(), run_serial_half()

    speedup = serial.wall_seconds / concurrent.wall_seconds if concurrent.wall_seconds else 0.0

    # The honest denominator. Ideal concurrent wall-clock is
    # ceil(n / concurrency) waves at the *serial* per-call latency; anything
    # faster than that is the provider being quicker this minute, not the
    # queue. Without this correction a measured 6.6x at concurrency 6 reads as
    # superlinear, which is not a thing.
    waves = math.ceil(len(cases) / limits.concurrency)
    ideal_wall = waves * serial.mean_latency
    latency_drift = concurrent.mean_latency / serial.mean_latency if serial.mean_latency else 1.0

    return {
        "n_tasks": len(cases),
        "concurrency": limits.concurrency,
        "serial_first": serial_first,
        "serial": serial.summary(),
        "concurrent": concurrent.summary(),
        "speedup": round(speedup, 2),
        "theoretical_max": limits.concurrency,
        "ideal_wall_seconds": round(ideal_wall, 2),
        # >1.0 means we beat the ideal, which can only come from per-call
        # latency drift between the two halves — reported, not hidden.
        "vs_ideal": round(ideal_wall / concurrent.wall_seconds, 2)
        if concurrent.wall_seconds
        else 0.0,
        "latency_drift": round(latency_drift, 2),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pairs", type=int, default=6)
    parser.add_argument("--concurrency", type=int, default=6)
    parser.add_argument("--judge", default="deepseek")
    parser.add_argument(
        "--trials", type=int, default=2, help="Counter-balanced: odd trials run serial first."
    )
    parser.add_argument("--out", default=str(RESULTS_DIR / "queue_bench.json"))
    args = parser.parse_args()

    cases = build_cases(limit=args.pairs, difficulty="subtle")
    judge_config = resolve_judge(args.judge)
    llm = LLMFactory.create_llm(
        provider="openai",
        api_key=judge_config["api_key"],
        model=judge_config["model"],
        base_url=judge_config["base_url"],
    )
    judge = StructuredJudge(llm, mode=JudgeMode.STRUCTURED)

    limits = RateLimits(
        rpm=RateLimits.paid_tier().rpm,
        tpm=RateLimits.paid_tier().tpm,
        concurrency=args.concurrency,
        name=f"bench-c{args.concurrency}",
    )

    print(f"Judge model: {judge_config['model']}")
    print(f"{len(cases)} judge calls, concurrency={args.concurrency}\n")

    trials = []
    for i in range(args.trials):
        serial_first = i % 2 == 0
        print(f"trial {i + 1} ({'serial' if serial_first else 'concurrent'} first):")
        trial = _bench(judge, cases, limits, serial_first=serial_first)
        print(
            f"    speed-up {trial['speedup']}x, "
            f"{trial['vs_ideal']}x vs ideal, "
            f"latency drift {trial['latency_drift']}x\n"
        )
        trials.append(trial)

    mean_speedup = sum(t["speedup"] for t in trials) / len(trials)
    report = {
        "n_tasks": len(cases),
        "concurrency": args.concurrency,
        "judge_model": judge_config["model"],
        "mean_speedup": round(mean_speedup, 2),
        "efficiency": round(mean_speedup / args.concurrency, 2),
        "trials": trials,
    }
    print(
        f"mean speed-up over {len(trials)} counter-balanced trials: "
        f"{report['mean_speedup']}x at concurrency {args.concurrency} "
        f"({report['efficiency']:.0%} of the concurrency cap)"
    )

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n→ {out}")


if __name__ == "__main__":
    main()
