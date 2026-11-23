"""
Unit tests for the 3 empirical benchmark & bad-case post-mortem suites:
- scripts/benchmark_badcase_postmortem.py
- scripts/benchmark_long_context_forgetting.py
- scripts/benchmark_async_chaos_sla.py
"""

import asyncio
from pathlib import Path

from scripts.benchmark_async_chaos_sla import run_async_chaos_benchmark
from scripts.benchmark_badcase_postmortem import (
    ALL_CLUSTERS,
    BadCaseRecord,
    classify_bad_case_cluster,
    cluster_bad_cases,
    run_badcase_postmortem,
)
from scripts.benchmark_common import compute_percentile, estimate_tokens
from scripts.benchmark_long_context_forgetting import (
    _build_synthetic_conversation,
    build_prompt_for_strategy,
    run_long_context_benchmark,
    score_constraint_retention,
)


def test_common_helpers():
    assert estimate_tokens("预算25万以内，不要纯电") > 0
    assert compute_percentile([10.0, 20.0, 30.0, 40.0, 50.0], 50) == 30.0
    assert compute_percentile([10.0, 20.0, 30.0, 40.0, 50.0], 95) >= 40.0


def test_badcase_clustering_and_postmortem_mock(tmp_path: Path):
    assert classify_bad_case_cluster("tool timeout exceeded") == "工具参数越界或超时"
    assert classify_bad_case_cluster("numeric hallucination detected") == "数值幻觉"
    assert classify_bad_case_cluster("negative exclusion violated") == "检索硬约束冲突"
    assert classify_bad_case_cluster("budget overwrite") == "抽取歧义误覆盖"

    recs = [
        BadCaseRecord(
            case_id="1",
            trace_id="t1",
            session_id="s1",
            persona="p1",
            turn_index=1,
            user_utterance="u",
            agent_reply="a",
            raw_reason="tool_timeout",
            cluster="工具参数越界或超时",
        )
    ]
    grouped = cluster_bad_cases(recs)
    assert set(grouped.keys()) == set(ALL_CLUSTERS)
    assert len(grouped["工具参数越界或超时"]) == 1

    report_md = tmp_path / "postmortem.md"
    reg_json = tmp_path / "regression.json"
    summary = run_badcase_postmortem(
        use_mock=True,
        max_turns=1,
        dlq_storage_dir=tmp_path / "dlq",
        report_path=report_md,
        regression_export_path=reg_json,
    )
    assert summary.total_episodes == 5
    assert summary.dlq_resolved_count == summary.dlq_total_attempted
    assert report_md.exists()
    assert reg_json.exists()


def test_long_context_strategies_and_mock_benchmark(tmp_path: Path):
    history, prefs = _build_synthetic_conversation(30)
    full_msgs = build_prompt_for_strategy("full_history", history, prefs, turn_idx=30)
    win_msgs = build_prompt_for_strategy("sliding_window_20", history, prefs, turn_idx=30)
    av_msgs = build_prompt_for_strategy("autovend_compact", history, prefs, turn_idx=30)

    full_tokens = sum(estimate_tokens(m["content"]) for m in full_msgs)
    av_tokens = sum(estimate_tokens(m["content"]) for m in av_msgs)
    assert av_tokens < full_tokens

    # Sliding window drops Turn 1 at 30 turns, whereas AutoVend retains all 4 constraints in PreferenceModel
    win_hits, total = score_constraint_retention("\n".join(m["content"] for m in win_msgs))
    av_hits, _ = score_constraint_retention("\n".join(m["content"] for m in av_msgs))
    assert win_hits < total
    assert av_hits == total

    report_md = tmp_path / "long_ctx.md"
    out_json = tmp_path / "long_ctx.json"
    payload = run_long_context_benchmark(
        use_mock=True,
        milestones=(10, 30),
        report_path=report_md,
        json_path=out_json,
    )
    assert len(payload["results"]) == 6
    assert report_md.exists()
    assert out_json.exists()


def test_async_chaos_sla_mock(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("APP_ENV", "test")
    report_md = tmp_path / "chaos.md"
    out_json = tmp_path / "chaos.json"
    payload = asyncio.run(
        run_async_chaos_benchmark(
            use_mock=True,
            concurrency_levels=(5, 10),
            report_path=report_md,
            json_path=out_json,
        )
    )
    assert len(payload["concurrency_metrics"]) == 2
    assert payload["chaos_metrics"]["idempotency_unique_executions"] == 1
    assert payload["chaos_metrics"]["idempotency_replay_hits"] == 9
    assert payload["chaos_metrics"]["tool_timeout_gracefully_degraded"] == payload["chaos_metrics"]["tool_timeout_injected"]
    assert payload["chaos_metrics"]["lock_contention_succeeded"] >= 1
    assert payload["chaos_metrics"]["lock_contention_rejected_429"] >= 1
    assert report_md.exists()
    assert out_json.exists()
