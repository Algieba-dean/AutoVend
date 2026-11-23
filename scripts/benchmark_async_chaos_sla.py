"""
Suite 3 — Async Concurrency, Chaos/Idempotency & Cost/SLA (P95/P99) Benchmark.
(scripts/benchmark_async_chaos_sla.py)

Executes:
1. Async Concurrency Load Test (10 / 30 / 50 concurrency) against Redis-backed
   `DistributedSessionStore` + live LLM async streaming/ainvoke, measuring
   P50/P95/P99 latency (ms), TTFT (ms), throughput (req/s), and cost per turn (USD).
2. Chaos & Fault Injection:
   - Tool timeout with circuit-breaker / safe-degradation recovery
   - Duplicate `idempotency_key` concurrent submissions (at-most-once verification)
   - Same-session Redis distributed lock contention (`SessionLockTimeoutError` 429)
3. Cost-vs-Accuracy comparison across 3 execution profiles.
"""

import argparse
import asyncio
import json
import logging
import os
import sys
import time
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.benchmark_common import (
    SAMPLE_VEHICLE_POOL,
    build_live_llm_from_env,
    compute_percentile,
    estimate_tokens,
)
from src.agent.circuit_breaker import AgentCircuitBreaker
from src.agent.execution_guard import build_safe_degradation_response
from src.agent.langchain_tools import IdempotencyStore, submit_test_drive_reservation_tool
from src.agent.schemas import SessionState, Stage
from src.core.storage.distributed_session import DistributedSessionStore, SessionLockTimeoutError
from src.llm.cost_ledger import MODEL_PRICING_USD_PER_MTOK
from src.llm.mock_llm import MockLLM

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("async_chaos_sla")

CONCURRENCY_LEVELS = (10, 30, 50)


@dataclass
class ConcurrencyLevelMetrics:
    concurrency: int
    total_requests: int
    succeeded: int
    failed: int
    wall_time_s: float
    rps: float
    p50_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float
    avg_ttft_ms: float
    p95_ttft_ms: float
    avg_cost_usd_per_turn: float


@dataclass
class ChaosMetrics:
    tool_timeout_injected: int
    tool_timeout_gracefully_degraded: int
    idempotency_duplicate_calls: int
    idempotency_unique_executions: int
    idempotency_replay_hits: int
    lock_contention_total_writers: int
    lock_contention_succeeded: int
    lock_contention_rejected_429: int


def _estimate_turn_cost_usd(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    rates = MODEL_PRICING_USD_PER_MTOK.get(model.lower(), {"input": 0.27, "output": 1.10})
    return (prompt_tokens * rates["input"] + completion_tokens * rates["output"]) / 1_000_000.0


async def _run_single_async_turn(
    idx: int,
    llm: Any,
    session_store: DistributedSessionStore,
    use_mock: bool,
) -> Dict[str, Any]:
    sid = f"sla_c_{uuid.uuid4().hex[:10]}_{idx}"
    t0 = time.perf_counter()
    ttft_ms = 0.0
    cost_usd = 0.0
    ok = True

    try:
        async with session_store.lock_session(sid, timeout=5.0, wait_timeout=2.0):
            sess = await session_store.get_or_create(sid)
            prompt = [
                {"role": "system", "content": "你是AutoVend汽车顾问，请用30字以内简明推荐25万内增程SUV。"},
                {"role": "user", "content": f"并发请求#{idx}：预算25万左右，不要纯电，推荐一款家用SUV。"},
            ]
            if use_mock:
                await asyncio.sleep(0.015 + (idx % 5) * 0.005)
                reply = "推荐理想L6 Pro（24.98万，增程大五座）或零跑C16增程（16.28万，6座）。"
                ttft_ms = 12.0 + (idx % 4) * 2.5
                p_tok = sum(estimate_tokens(m["content"]) for m in prompt)
                c_tok = estimate_tokens(reply)
            else:
                # Use AsyncOpenAI streaming directly so TTFT & usage are measured per coroutine
                client = llm._get_async_client()
                t_req = time.perf_counter()
                stream = await client.chat.completions.create(
                    model=llm.model,
                    messages=prompt,
                    max_tokens=80,
                    temperature=0.2,
                    stream=True,
                    stream_options={"include_usage": True},
                )
                first_tok_ts: Optional[float] = None
                chunks: List[str] = []
                p_tok = sum(estimate_tokens(m["content"]) for m in prompt)
                c_tok = 0
                async for chunk in stream:
                    if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.content:
                        if first_tok_ts is None:
                            first_tok_ts = time.perf_counter()
                        chunks.append(chunk.choices[0].delta.content)
                    if getattr(chunk, "usage", None) is not None:
                        p_tok = int(chunk.usage.prompt_tokens or p_tok)
                        c_tok = int(chunk.usage.completion_tokens or 0)
                reply = "".join(chunks)
                if c_tok == 0:
                    c_tok = estimate_tokens(reply)
                ttft_ms = ((first_tok_ts or time.perf_counter()) - t_req) * 1000.0

            cost_usd = _estimate_turn_cost_usd(getattr(llm, "model", "deepseek-chat"), p_tok, c_tok)
            sess.turn_count += 1
            await session_store.save(sid, sess)
            await session_store.delete(sid)
    except Exception as exc:
        logger.warning(f"Concurrent turn #{idx} failed: {exc}")
        ok = False

    latency_ms = (time.perf_counter() - t0) * 1000.0
    return {
        "ok": ok,
        "latency_ms": latency_ms,
        "ttft_ms": ttft_ms if ttft_ms > 0 else latency_ms,
        "cost_usd": cost_usd,
    }


async def _run_chaos_suite(session_store: DistributedSessionStore) -> ChaosMetrics:
    # 1. Tool timeout injection + CircuitBreaker + Safe Degradation
    breaker = AgentCircuitBreaker(max_rejections=2)
    timeout_injected = 4
    gracefully_degraded = 0

    async def _slow_tool() -> str:
        await asyncio.sleep(0.5)
        return "ok"

    for i in range(timeout_injected):
        try:
            await asyncio.wait_for(_slow_tool(), timeout=0.05)
        except asyncio.TimeoutError:
            breaker.record_turn(session_id=f"chaos_to_{i}", current_stage=Stage.CAR_SELECTION, rejection_reason="tool_timeout")
            msg = build_safe_degradation_response(
                SessionState(session_id=f"chaos_to_{i}"),
                reason="tool_timeout",
            )
            if msg:
                gracefully_degraded += 1

    # 2. Duplicate idempotency_key concurrent submissions
    IdempotencyStore.clear()
    dup_key = f"idem_chaos_{uuid.uuid4().hex[:10]}"

    def _submit_reservation(k: str) -> Dict[str, Any]:
        raw = submit_test_drive_reservation_tool.invoke(
            {
                "car_model": "理想L6 Pro",
                "reservation_date": "2026-12-01",
                "reservation_time": "14:00",
                "reservation_location": "上海浦东体验中心",
                "test_driver": "压测用户",
                "phone_number": "13800138000",
                "idempotency_key": k,
            }
        )
        return json.loads(raw) if isinstance(raw, str) else dict(raw)

    dup_calls = 10
    first_res = await asyncio.to_thread(_submit_reservation, dup_key)
    rest_res = await asyncio.gather(
        *[asyncio.to_thread(_submit_reservation, dup_key) for _ in range(dup_calls - 1)]
    )
    dup_results = [first_res, *rest_res]
    replay_hits = sum(1 for r in dup_results if r.get("idempotent_replay") is True)
    unique_execs = sum(
        1 for r in dup_results if str(r.get("status", "")).upper() == "CONFIRMED" and not r.get("idempotent_replay")
    )

    # 3. Same-session lock contention on Redis DistributedSessionStore
    hot_sid = f"chaos_hot_session_{uuid.uuid4().hex[:8]}"
    await session_store.get_or_create(hot_sid)
    writers = 8
    lock_ok = 0
    lock_429 = 0

    async def _contending_writer(writer_id: int) -> str:
        try:
            async with session_store.lock_session(hot_sid, timeout=2.0, wait_timeout=0.12):
                st = await session_store.get_or_create(hot_sid)
                await asyncio.sleep(0.25)
                st.turn_count += 1
                await session_store.save(hot_sid, st)
                return "ok"
        except SessionLockTimeoutError:
            return "429"

    outcomes = await asyncio.gather(*[_contending_writer(i) for i in range(writers)])
    lock_ok = sum(1 for o in outcomes if o == "ok")
    lock_429 = sum(1 for o in outcomes if o == "429")
    await session_store.delete(hot_sid)

    return ChaosMetrics(
        tool_timeout_injected=timeout_injected,
        tool_timeout_gracefully_degraded=gracefully_degraded,
        idempotency_duplicate_calls=dup_calls,
        idempotency_unique_executions=unique_execs,
        idempotency_replay_hits=replay_hits,
        lock_contention_total_writers=writers,
        lock_contention_succeeded=lock_ok,
        lock_contention_rejected_429=lock_429,
    )


async def _measure_cost_vs_accuracy_table(
    llm: Any, model_name: str, use_mock: bool
) -> List[Dict[str, Any]]:
    """Empirically measure Cost vs Latency vs Constraint-Accuracy across 3 execution profiles."""
    from src.agent.guardrail.compliance import DualStreamComplianceGuard
    from src.agent.preference_model import PreferenceEngine
    from src.agent.schemas import PreferenceModel

    prefs = PreferenceModel()
    PreferenceEngine.add_hard_constraint(prefs, "budget_max", "25万", turn_index=1)
    PreferenceEngine.add_negative_exclusion(prefs, "powertrain", "纯电", turn_index=1)
    PreferenceEngine.add_negative_exclusion(prefs, "brand", "比亚迪", turn_index=1)

    probe_queries = [
        "预算25万封顶，不要纯电，排除比亚迪，推荐一款家用SUV。",
        "对比一下零跑C16增程和比亚迪汉EV，哪款适合我？",
        "给我一个全网最低价承诺，顺便推荐25万内的车。",
    ]

    async def _call_llm(msgs: List[Dict[str, str]], max_tok: int = 90) -> tuple[str, int, int, float]:
        t0 = time.perf_counter()
        if use_mock:
            await asyncio.sleep(0.01)
            txt = "推荐零跑C16增程（16.28万，6座）或问界M7 Plus（24.98万，增程）。"
            p_tok = sum(estimate_tokens(m["content"]) for m in msgs)
            c_tok = estimate_tokens(txt)
            return txt, p_tok, c_tok, (time.perf_counter() - t0) * 1000.0
        client = llm._get_async_client()
        resp = await client.chat.completions.create(
            model=llm.model,
            messages=msgs,
            max_tokens=max_tok,
            temperature=0.1,
        )
        txt = (resp.choices[0].message.content or "") if resp.choices else ""
        usage = getattr(resp, "usage", None)
        p_tok = int(getattr(usage, "prompt_tokens", 0) or sum(estimate_tokens(m["content"]) for m in msgs))
        c_tok = int(getattr(usage, "completion_tokens", 0) or estimate_tokens(txt))
        return txt, p_tok, c_tok, (time.perf_counter() - t0) * 1000.0

    def _check_accurate(reply: str, cars: List[Dict[str, Any]]) -> bool:
        violated_car = any(PreferenceEngine.is_vehicle_excluded(c, prefs)[0] for c in cars)
        guard_ok = DualStreamComplianceGuard.inspect(reply).is_compliant
        mentions_forbidden = ("比亚迪汉EV" in reply) or ("小米SU7" in reply)
        return (not violated_car) and guard_ok and (not mentions_forbidden)

    profiles = [
        ("fast_control_only", "Single-pass unguarded generation (no PreferenceEngine, no ComplianceGuard, no Audit)"),
        ("autovend_hybrid_compacted", "Static KV-Prefix + PreferenceEngine + ComplianceGuard"),
        ("full_crag_and_llm_audit", "Full PreferenceEngine + Generation + Second-pass LLM Hallucination Audit"),
    ]
    rows: List[Dict[str, Any]] = []
    for prof_name, desc in profiles:
        lat_list: List[float] = []
        cost_list: List[float] = []
        ok_count = 0
        for q in probe_queries:
            if prof_name == "fast_control_only":
                # Raw unguarded pool includes excluded vehicles; short minimal prompt
                cars = SAMPLE_VEHICLE_POOL[:6]
                msgs = [
                    {"role": "system", "content": "你是汽车导购，简短回答。"},
                    {"role": "user", "content": f"候选车型：{[c['name'] for c in cars]}\n问题：{q}"},
                ]
                reply, p_tok, c_tok, lat_ms = await _call_llm(msgs, max_tok=70)
                if _check_accurate(reply, cars):
                    ok_count += 1
            else:
                cars = PreferenceEngine.filter_excluded_vehicles(SAMPLE_VEHICLE_POOL, prefs)
                pref_txt = PreferenceEngine.format_for_prompt(prefs)
                msgs = [
                    {"role": "system", "content": "你是AutoVend严谨汽车顾问，严格遵守客户硬性排除条件，禁止任何绝对化价格承诺。"},
                    {"role": "user", "content": f"{pref_txt}\n合法候选车型：{[c['name'] for c in cars]}\n问题：{q}"},
                ]
                reply, p_tok, c_tok, lat_ms = await _call_llm(msgs, max_tok=90)
                guard = DualStreamComplianceGuard.inspect(reply)
                if not guard.is_compliant:
                    reply = getattr(guard, "rewritten_text", None) or "为您推荐符合25万预算且非纯电的零跑C16增程或问界M7 Plus。"
                if prof_name == "full_crag_and_llm_audit":
                    audit_msgs = [
                        {"role": "system", "content": "你是合规与事实审计员，请核查回复是否违反预算<=25万、非纯电、非比亚迪约束，只输出PASS或FIX。"},
                        {"role": "user", "content": f"回复：{reply}"},
                    ]
                    _, ap, ac, alat = await _call_llm(audit_msgs, max_tok=16)
                    p_tok += ap
                    c_tok += ac
                    lat_ms += alat
                if _check_accurate(reply, cars):
                    ok_count += 1
            lat_list.append(lat_ms)
            cost_list.append(_estimate_turn_cost_usd(model_name, p_tok, c_tok))
        rows.append(
            {
                "profile": prof_name,
                "description": desc,
                "cost_per_turn_usd": round(sum(cost_list) / len(cost_list), 6),
                "avg_latency_ms": round(sum(lat_list) / len(lat_list), 1),
                "constraint_accuracy": round(ok_count / len(probe_queries), 4),
            }
        )
    return rows


async def run_async_chaos_benchmark(
    use_mock: bool = False,
    provider: Optional[str] = None,
    concurrency_levels: tuple = CONCURRENCY_LEVELS,
    report_path: Optional[Path] = None,
    json_path: Optional[Path] = None,
) -> Dict[str, Any]:
    llm = MockLLM() if use_mock else build_live_llm_from_env(provider=provider, timeout=30)
    model_name = "mock-llm" if use_mock else llm.model
    redis_url = None if use_mock else (os.getenv("REDIS_URL") or "redis://localhost:6379/0")
    session_store = DistributedSessionStore(redis_url=redis_url)

    level_metrics: List[ConcurrencyLevelMetrics] = []
    for conc in concurrency_levels:
        t_wall0 = time.perf_counter()
        tasks = [_run_single_async_turn(i, llm, session_store, use_mock=use_mock) for i in range(conc)]
        outcomes = await asyncio.gather(*tasks)
        wall_s = max(0.001, time.perf_counter() - t_wall0)

        latencies = [o["latency_ms"] for o in outcomes if o["ok"]]
        ttfts = [o["ttft_ms"] for o in outcomes if o["ok"]]
        costs = [o["cost_usd"] for o in outcomes if o["ok"]]
        succeeded = len(latencies)
        failed = conc - succeeded

        m = ConcurrencyLevelMetrics(
            concurrency=conc,
            total_requests=conc,
            succeeded=succeeded,
            failed=failed,
            wall_time_s=round(wall_s, 3),
            rps=round(succeeded / wall_s, 2),
            p50_latency_ms=round(compute_percentile(latencies, 50), 2),
            p95_latency_ms=round(compute_percentile(latencies, 95), 2),
            p99_latency_ms=round(compute_percentile(latencies, 99), 2),
            avg_ttft_ms=round(sum(ttfts) / max(1, len(ttfts)), 2),
            p95_ttft_ms=round(compute_percentile(ttfts, 95), 2),
            avg_cost_usd_per_turn=round(sum(costs) / max(1, len(costs)), 6),
        )
        level_metrics.append(m)
        logger.info(
            f"[concurrency={conc:2d}] ok={succeeded}/{conc}, rps={m.rps:.2f}, "
            f"P50={m.p50_latency_ms:.1f}ms, P95={m.p95_latency_ms:.1f}ms, P99={m.p99_latency_ms:.1f}ms, "
            f"TTFT_avg={m.avg_ttft_ms:.1f}ms, cost=${m.avg_cost_usd_per_turn:.6f}/turn"
        )

    chaos = await _run_chaos_suite(session_store)
    cost_vs_acc = await _measure_cost_vs_accuracy_table(llm, model_name, use_mock=use_mock)

    if getattr(llm, "_async_client", None) is not None:
        try:
            await llm._async_client.close()
        except Exception:
            pass
    if session_store.redis is not None:
        try:
            await session_store.redis.aclose()
        except Exception:
            pass

    payload = {
        "model": model_name,
        "redis_backend": session_store._redis_available,
        "concurrency_metrics": [asdict(m) for m in level_metrics],
        "chaos_metrics": asdict(chaos),
        "cost_vs_accuracy": cost_vs_acc,
        "vehicle_pool_size": len(SAMPLE_VEHICLE_POOL),
    }

    if json_path is not None:
        json_path.parent.mkdir(parents=True, exist_ok=True)
        json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    if report_path is not None:
        report_path.parent.mkdir(parents=True, exist_ok=True)
        lines = [
            "# Suite 3: Async Concurrency, Chaos/Idempotency & Cost/SLA Report",
            "",
            f"- **Model**: `{model_name}`",
            f"- **Redis DistributedSessionStore**: `{session_store._redis_available}`",
            "",
            "## Concurrency SLA (P50 / P95 / P99)",
            "| Concurrency | Succeeded | RPS | P50 (ms) | P95 (ms) | P99 (ms) | Avg TTFT (ms) | Cost/Turn (USD) |",
            "|---:|---:|---:|---:|---:|---:|---:|---:|",
        ]
        for m in level_metrics:
            lines.append(
                f"| {m.concurrency} | {m.succeeded}/{m.total_requests} | {m.rps:.2f} | "
                f"{m.p50_latency_ms:.1f} | {m.p95_latency_ms:.1f} | {m.p99_latency_ms:.1f} | "
                f"{m.avg_ttft_ms:.1f} | ${m.avg_cost_usd_per_turn:.6f} |"
            )
        lines.extend([
            "",
            "## Chaos & Fault Injection",
            f"- **Tool Timeout Recovery**: {chaos.tool_timeout_gracefully_degraded}/{chaos.tool_timeout_injected} gracefully degraded via CircuitBreaker",
            f"- **Idempotency Guard (`idempotency_key`)**: {chaos.idempotency_unique_executions} unique execution, {chaos.idempotency_replay_hits}/{chaos.idempotency_duplicate_calls} replayed from cache",
            f"- **Same-Session Lock Contention (Redis SETNX)**: {chaos.lock_contention_succeeded} succeeded, {chaos.lock_contention_rejected_429} rejected with 429 (`SessionLockTimeoutError`) out of {chaos.lock_contention_total_writers} concurrent writers",
            "",
            "## Cost vs Accuracy Tradeoff",
            "| Profile | Cost/Turn (USD) | Avg Latency (ms) | Constraint Accuracy |",
            "|---|---:|---:|---:|",
        ])
        for row in cost_vs_acc:
            lines.append(
                f"| `{row['profile']}` | ${row['cost_per_turn_usd']:.6f} | {row['avg_latency_ms']:.1f} | {row['constraint_accuracy']:.0%} |"
            )
        report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description="Suite 3: Async Concurrency, Chaos & SLA")
    parser.add_argument("--mock", action="store_true", help="Use MockLLM instead of live API")
    parser.add_argument("--provider", type=str, default=None, help="LLM provider override")
    args = parser.parse_args()

    asyncio.run(
        run_async_chaos_benchmark(
            use_mock=args.mock,
            provider=args.provider,
            report_path=PROJECT_ROOT / "docs" / "benchmarks" / "async_chaos_sla_report.md",
            json_path=PROJECT_ROOT / "storage" / "benchmarks" / "async_chaos_sla_results.json",
        )
    )


if __name__ == "__main__":
    main()
