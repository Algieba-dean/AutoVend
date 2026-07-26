"""
Hybrid-routing benchmark: local vLLM vs cloud API on the control path.

Produces the numbers that justify (or refute) serving extraction and query
parsing locally: TTFT and end-to-end latency percentiles per backend, plus the
cloud tokens the local route avoided. Run it whenever the local server or the
routing policy changes — the point of measuring is that the split stays a
decision, not a belief.

The workload is the real one: extraction prompts rendered from the agent's own
templates and parser prompts from `LLMParser`, over golden-set queries — not
synthetic "hello" calls, which would flatter TTFT by skipping prefill.

Usage:
    python -m src.eval.routing_bench --n 30
    python -m src.eval.routing_bench --n 30 --routes local cloud
"""

import argparse
import json
import statistics
import sys
from pathlib import Path
from typing import Dict, List, Optional, Sequence

from src.eval.golden_set import load_golden_set
from src.eval.runner import RESULTS_DIR
from src.llm.telemetry import PRICING_USD_PER_MTOK
from src.utils.logger import get_logger

logger = get_logger(__name__)

#: Above this share of failed calls a route's percentiles are flagged
#: unreliable. Free-tier providers exhaust daily token budgets mid-run, and a
#: number computed from the surviving third is worse than no number.
MAX_FAILURE_RATE = 0.1

#: Conversation snippets that drive the extraction prompt, paired with golden
#: queries for the parser prompt. Small but realistic: Chinese and English,
#: sparse and dense information turns.
EXTRACTION_TURNS = [
    "你好，我想买一辆车，主要是家用",
    "我叫张伟，35岁，工程师，家里三口人，住上海，有固定车位",
    "预算大概30到40万，想要纯电的，最好是SUV",
    "I need something with 7 seats for my family, budget around 50k",
    "平时上下班开，周末偶尔跑长途，比较在意续航和舒适性",
    "我夫人也开这台车，她驾龄比较短，安全配置要好",
]


def _extraction_prompts(n: int) -> List[str]:
    """Render real extraction prompts from the agent's own template."""
    from src.agent.extractors.profile_extractor import PROFILE_EXTRACTION_PROMPT

    prompts = []
    for i in range(n):
        turn = EXTRACTION_TURNS[i % len(EXTRACTION_TURNS)]
        prompts.append(
            PROFILE_EXTRACTION_PROMPT.format(conversation=f"User: {turn}", current_profile="{}")
        )
    return prompts


def _parser_prompts(n: int) -> List[List[Dict[str, str]]]:
    """Render real query-parser chats over golden-set queries."""
    from src.filter.llm_parser import SYSTEM_PROMPT

    queries = load_golden_set()
    return [
        [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": queries[i % len(queries)].query},
        ]
        for i in range(n)
    ]


def _build_backend(route: str):
    """
    Build a backend exactly as production does.

    Routed through `build_default_router` rather than constructed here, so the
    benchmark cannot drift from the deployed configuration — an earlier version
    built the local client directly and silently left reasoning-model
    chain-of-thought enabled, inflating completion tokens 4x and latency 5x
    versus what the router actually sends.
    """
    from src.llm.router import build_default_router

    router = build_default_router()

    if route == "local":
        if router.local is None:
            raise SystemExit("LOCAL_LLM_BASE_URL is not set — start ./scripts/serve_local_llm.sh")
        return router.local
    if route == "cloud":
        if router.cloud is None:
            raise SystemExit("No cloud credentials configured.")
        return router.cloud
    raise ValueError(route)


def bench_route(route: str, n: int) -> Dict:
    """Run the control-path workload against one backend."""
    backend = _build_backend(route)
    if not backend.is_available():
        raise SystemExit(f"{route} backend ({backend.base_url}) is not reachable")

    extraction = _extraction_prompts(n)
    parsing = _parser_prompts(n)

    ttfts: List[float] = []
    latencies: List[float] = []
    prompt_tokens = 0
    completion_tokens = 0
    failures = 0

    import time

    # Interleave the two workloads the way a real turn does.
    for i in range(n):
        for payload, method in ((extraction[i], "complete"), (parsing[i], "chat")):
            started = time.perf_counter()
            try:
                getattr(backend, method)(payload, max_tokens=256, temperature=0.0)
            except Exception as exc:
                failures += 1
                logger.warning(f"[{route}] call failed: {exc}")
                continue
            latencies.append(time.perf_counter() - started)
            if backend.last_ttft_s is not None:
                ttfts.append(backend.last_ttft_s)
            usage = backend.last_usage or {}
            prompt_tokens += usage.get("prompt_tokens", 0)
            completion_tokens += usage.get("completion_tokens", 0)

    def pct(vals: List[float], p: float) -> float:
        if not vals:
            return 0.0
        ordered = sorted(vals)
        return ordered[min(len(ordered) - 1, max(0, int(round(p / 100 * len(ordered) + 0.5)) - 1))]

    cloud_price = PRICING_USD_PER_MTOK["cloud"]
    cloud_equiv_cost = (
        prompt_tokens * cloud_price["input"] + completion_tokens * cloud_price["output"]
    ) / 1_000_000

    # Percentiles over a heavily-truncated sample look like measurements but
    # are not. A rate-limited cloud run that loses two thirds of its calls
    # would otherwise report a confident-looking TTFT drawn from whichever
    # requests happened to slip through.
    failure_rate = failures / (2 * n) if n else 0.0
    if failure_rate > MAX_FAILURE_RATE:
        logger.error(
            f"[{route}] {failures}/{2 * n} calls failed ({failure_rate:.0%}) — "
            "percentiles suppressed; results are not quotable"
        )

    return {
        "route": route,
        "model": backend.model,
        "n_calls": 2 * n,
        "n_failed": failures,
        "reliable": failure_rate <= MAX_FAILURE_RATE,
        "ttft_mean_s": round(statistics.mean(ttfts), 4) if ttfts else None,
        "ttft_p50_s": round(pct(ttfts, 50), 4) if ttfts else None,
        "ttft_p95_s": round(pct(ttfts, 95), 4) if ttfts else None,
        "ttft_p99_s": round(pct(ttfts, 99), 4) if ttfts else None,
        "latency_mean_s": round(statistics.mean(latencies), 4) if latencies else None,
        "latency_p95_s": round(pct(latencies, 95), 4) if latencies else None,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "cost_at_cloud_rates_usd": round(cloud_equiv_cost, 6),
    }


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--n", type=int, default=30, help="Turns per route (2 calls per turn)")
    parser.add_argument(
        "--routes", nargs="+", default=["local", "cloud"], choices=["local", "cloud"]
    )
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args(argv)

    results = []
    for route in args.routes:
        print(f"Benchmarking {route} ({args.n} turns, {2 * args.n} calls)...")
        results.append(bench_route(route, args.n))

    report = {"n_turns": args.n, "routes": results}
    out = args.out or (RESULTS_DIR / "routing_bench.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    header = (
        f"{'route':<8} {'model':<28} {'TTFT p50':>9} {'p95':>8} "
        f"{'p99':>8} {'lat p95':>8} {'$@cloud':>9}"
    )
    print(f"\n{header}")
    for r in results:
        flag = "" if r["reliable"] else f"  ⚠ {r['n_failed']}/{r['n_calls']} calls failed"
        print(
            f"{r['route']:<8} {r['model'][:27]:<28} "
            f"{r['ttft_p50_s'] if r['ttft_p50_s'] is not None else '—':>9} "
            f"{r['ttft_p95_s'] if r['ttft_p95_s'] is not None else '—':>8} "
            f"{r['ttft_p99_s'] if r['ttft_p99_s'] is not None else '—':>8} "
            f"{r['latency_p95_s'] if r['latency_p95_s'] is not None else '—':>8} "
            f"{r['cost_at_cloud_rates_usd']:>9}{flag}"
        )

    if any(not r["reliable"] for r in results):
        print(
            "\n⚠ At least one route lost too many calls to be quotable. "
            "Re-run when the provider quota resets.",
            file=sys.stderr,
        )

    if len(results) == 2:
        local = next((r for r in results if r["route"] == "local"), None)
        if local:
            print(
                f"\nCloud tokens avoided by the local route: "
                f"{local['prompt_tokens'] + local['completion_tokens']} "
                f"(≈ ${local['cost_at_cloud_rates_usd']} at cloud rates)"
            )
    print(f"\nReport: {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
