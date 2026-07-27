"""
Tests for the evaluation gateway: rate limiting, the async queue, judge
parsing, alignment statistics, and batch packaging.

Every test here runs without a network call. The judge's *quality* needs a real
model and lives in `src.eval.judge_ab`; what is testable offline is the
machinery around it — and that machinery is where the silent failures were
(see docs/record.md #40-#44).
"""

import asyncio
import json
import time

import pytest

from src.eval.alignment import (
    KAPPA_GATE,
    alignment_report,
    cohens_kappa,
    load_review_queue,
    quadratic_kappa,
    sample_for_review,
    write_review_queue,
)
from src.eval.async_runner import EvalTask, run_queue_sync, run_serial
from src.eval.batch_api import (
    MAX_BATCH_BYTES,
    BatchRequest,
    parse_results,
    reconcile,
    write_batch,
)
from src.eval.judge import (
    JudgeMode,
    StructuredJudge,
    parse_verdict,
    verify_quotes,
)
from src.eval.rate_limit import (
    MAX_BACKOFF_SECONDS,
    RateLimiter,
    RateLimits,
    TokenBucket,
    _backoff_delay,
    _is_retryable,
    _retry_after,
    estimate_tokens,
)

# ── Rate limiting ──────────────────────────────────────────────


class TestTokenBucket:
    def test_burst_up_to_capacity_is_free(self):
        async def go():
            bucket = TokenBucket(rate=10, capacity=5)
            waits = [await bucket.acquire(1) for _ in range(5)]
            return waits

        assert asyncio.run(go()) == [0.0] * 5

    def test_exceeding_capacity_blocks_until_refilled(self):
        async def go():
            bucket = TokenBucket(rate=100, capacity=2)
            await bucket.acquire(2)
            started = time.monotonic()
            await bucket.acquire(2)
            return time.monotonic() - started

        # 2 tokens at 100/s ≈ 20ms. Generous bound: this asserts "it waited",
        # not a precise duration, which would be flaky under CI scheduling.
        elapsed = asyncio.run(go())
        assert 0.005 < elapsed < 1.0

    def test_request_larger_than_capacity_is_clamped_not_deadlocked(self):
        """A prompt bigger than the whole bucket must not hang the run."""

        async def go():
            bucket = TokenBucket(rate=1000, capacity=10)
            return await asyncio.wait_for(bucket.acquire(999), timeout=2.0)

        assert asyncio.run(go()) >= 0.0

    def test_refill_is_continuous_not_windowed(self):
        async def go():
            bucket = TokenBucket(rate=100, capacity=100)
            await bucket.acquire(100)
            await asyncio.sleep(0.05)
            return bucket.available

        # ~5 tokens back after 50ms. A window-reset limiter would still be at 0
        # until the boundary, then hand back all 100 at once.
        available = asyncio.run(go())
        assert 1 < available < 50


class TestRetryPolicy:
    @pytest.mark.parametrize(
        "message,expected",
        [
            ("429 Too Many Requests", True),
            ("rate_limit_exceeded", True),
            ("503 Service Unavailable", True),
            ("Connection reset by peer", True),
            ("Read timed out", True),
            ("400 Bad Request: invalid model", False),
            ("401 Unauthorized", False),
        ],
    )
    def test_only_transient_errors_retry(self, message, expected):
        """Retrying a 400 burns quota to reproduce a bug."""
        assert _is_retryable(Exception(message)) is expected

    def test_retry_after_parsed_from_groq_message_body(self):
        exc = Exception("Rate limit reached. Please try again in 7m31.008s")
        assert _retry_after(exc) == pytest.approx(451.008, abs=0.01)

    def test_retry_after_parsed_from_header_style(self):
        assert _retry_after(Exception("retry-after: 12")) == 12.0

    def test_no_hint_returns_none(self):
        assert _retry_after(Exception("500 Internal Server Error")) is None

    def test_backoff_honours_hint_but_caps_it(self):
        exc = Exception("Please try again in 45m0.0s")
        assert _backoff_delay(0, exc) == MAX_BACKOFF_SECONDS

    def test_backoff_is_jittered_within_exponential_ceiling(self):
        exc = Exception("429")
        delays = [_backoff_delay(3, exc) for _ in range(50)]
        assert all(0 <= d <= 8.0 for d in delays)
        # Full jitter, not fixed backoff: a whole queue retrying in lockstep is
        # what makes the second wave of 429s worse than the first.
        assert len(set(delays)) > 1

    def test_backoff_ceiling_never_exceeds_cap(self):
        exc = Exception("429")
        assert all(_backoff_delay(a, exc) <= MAX_BACKOFF_SECONDS for a in range(12))


class TestRateLimiter:
    def test_retry_loop_survives_transient_then_succeeds(self, monkeypatch):
        """Regression: `except ... as exc` unbinds `exc`, so reading it after
        the block raised NameError on the very first retry."""
        calls = {"n": 0}
        monkeypatch.setattr("src.eval.rate_limit._backoff_delay", lambda attempt, exc: 0.0)

        async def flaky():
            calls["n"] += 1
            if calls["n"] < 3:
                raise Exception("503 Service Unavailable")
            return "ok"

        async def go():
            limiter = RateLimiter(limits=RateLimits(rpm=600, tpm=60_000, concurrency=4))
            result = await limiter.call(flaky)
            return result, limiter.stats

        result, stats = asyncio.run(go())
        assert result == "ok"
        assert calls["n"] == 3
        assert stats.retries == 2

    def test_non_retryable_raises_immediately(self):
        def bad():
            raise ValueError("400 Bad Request")

        async def go():
            limiter = RateLimiter(limits=RateLimits(rpm=600, tpm=60_000, concurrency=2))
            with pytest.raises(ValueError):
                await limiter.call(bad)
            return limiter.stats

        stats = asyncio.run(go())
        assert stats.retries == 0
        assert stats.failures == 1

    def test_semaphore_caps_concurrent_calls(self):
        state = {"live": 0, "peak": 0}

        async def tracked():
            state["live"] += 1
            state["peak"] = max(state["peak"], state["live"])
            await asyncio.sleep(0.02)
            state["live"] -= 1
            return 1

        async def go():
            limiter = RateLimiter(limits=RateLimits(rpm=6000, tpm=600_000, concurrency=3))
            await asyncio.gather(*(limiter.call(tracked) for _ in range(12)))

        asyncio.run(go())
        assert state["peak"] <= 3

    def test_sync_callable_runs_off_the_event_loop(self):
        """A blocking client on the loop thread would serialise the queue and
        make the concurrency setting a lie."""
        state = {"peak": 0, "live": 0}

        def blocking():
            state["live"] += 1
            state["peak"] = max(state["peak"], state["live"])
            time.sleep(0.05)
            state["live"] -= 1
            return 1

        async def go():
            limiter = RateLimiter(limits=RateLimits(rpm=6000, tpm=600_000, concurrency=4))
            await asyncio.gather(*(limiter.call(blocking) for _ in range(8)))

        asyncio.run(go())
        assert state["peak"] > 1


class TestTokenEstimation:
    def test_cjk_counted_heavier_than_ascii(self):
        assert estimate_tokens("汽车推荐" * 10) > estimate_tokens("car" * 10)

    def test_estimate_overshoots_rather_than_under(self):
        # Under-estimating costs a 429; over-estimating costs throughput.
        assert estimate_tokens("续航里程是多少") >= 7


# ── Async queue ────────────────────────────────────────────────


class TestAsyncQueue:
    def test_results_return_in_submission_order(self):
        """Out-of-order rows make every baseline diff unreadable."""

        def make(i):
            def fn():
                time.sleep(0.03 if i % 2 else 0.001)
                return i

            return fn

        tasks = [EvalTask(key=f"t{i}", fn=make(i)) for i in range(8)]
        report = run_queue_sync(tasks, limits=RateLimits(rpm=6000, tpm=600_000, concurrency=8))
        assert [r.key for r in report.results] == [f"t{i}" for i in range(8)]
        assert [r.value for r in report.results] == list(range(8))

    def test_one_failure_does_not_cancel_siblings(self):
        def boom():
            raise RuntimeError("400 malformed record")

        tasks = [
            EvalTask(key="ok1", fn=lambda: 1),
            EvalTask(key="bad", fn=boom),
            EvalTask(key="ok2", fn=lambda: 2),
        ]
        report = run_queue_sync(tasks, limits=RateLimits(rpm=6000, tpm=600_000, concurrency=3))
        assert report.n_ok == 2
        assert report.n_failed == 1
        assert [r.key for r in report.results] == ["ok1", "bad", "ok2"]

    def test_concurrent_beats_serial_on_io_bound_work(self):
        def slow():
            time.sleep(0.05)
            return 1

        tasks = [EvalTask(key=f"t{i}", fn=slow) for i in range(8)]
        serial = run_serial(tasks)
        concurrent = run_queue_sync(tasks, limits=RateLimits(rpm=6000, tpm=600_000, concurrency=8))
        assert concurrent.wall_seconds < serial.wall_seconds / 2

    def test_progress_callback_fires_once_per_task(self):
        seen = []
        tasks = [EvalTask(key=f"t{i}", fn=lambda: 1) for i in range(5)]
        run_queue_sync(
            tasks,
            limits=RateLimits(rpm=6000, tpm=600_000, concurrency=5),
            on_progress=lambda done, total: seen.append((done, total)),
        )
        assert len(seen) == 5
        assert seen[-1] == (5, 5)

    def test_empty_queue_is_not_an_error(self):
        report = run_queue_sync([])
        assert report.n_tasks == 0
        assert report.throughput == 0.0


# ── Alignment statistics ───────────────────────────────────────


class TestCohensKappa:
    def test_perfect_agreement(self):
        assert cohens_kappa([1, 0, 1, 0], [1, 0, 1, 0]) == 1.0

    def test_total_disagreement_is_negative(self):
        assert cohens_kappa([1, 1, 0, 0], [0, 0, 1, 1]) < 0

    def test_majority_class_guessing_scores_near_zero(self):
        """The whole reason kappa is used instead of raw agreement."""
        human = [True] * 17 + [False] * 3
        always_pass = [True] * 20
        raw = sum(1 for a, b in zip(human, always_pass) if a == b) / 20
        assert raw == 0.85  # looks respectable
        assert cohens_kappa(human, always_pass) == 0.0  # is worthless

    def test_unanimous_identical_raters_report_perfect(self):
        assert cohens_kappa([True] * 10, [True] * 10) == 1.0

    def test_unanimous_but_opposite_raters_report_zero(self):
        assert cohens_kappa([True] * 10, [False] * 10) == 0.0

    def test_mismatched_lengths_rejected(self):
        with pytest.raises(ValueError):
            cohens_kappa([1, 2], [1])

    def test_empty_is_zero_not_a_crash(self):
        assert cohens_kappa([], []) == 0.0


class TestQuadraticKappa:
    def test_near_misses_cost_less_than_inversions(self):
        human = [5, 4, 5, 4, 0, 1]
        generous = [4, 3, 4, 3, 0, 1]  # consistently one point high
        inverted = [0, 1, 0, 1, 5, 4]
        assert quadratic_kappa(generous, human) > quadratic_kappa(inverted, human)

    def test_identical_ordinal_scores_are_perfect(self):
        assert quadratic_kappa([0, 3, 5], [0, 3, 5]) == pytest.approx(1.0)

    def test_single_level_degenerate_case(self):
        assert quadratic_kappa([3, 3, 3], [3, 3, 3]) == 1.0


class TestAlignmentReport:
    def test_reports_baseline_alongside_agreement(self):
        judge = [1.0] * 18 + [0.0] * 2
        human = [1.0] * 17 + [0.0] * 3
        report = alignment_report(judge, human)
        assert report.n == 20
        assert report.majority_baseline == pytest.approx(0.85)
        assert report.raw_agreement >= report.majority_baseline

    def test_disagreements_are_itemised(self):
        report = alignment_report([1.0, 0.0, 1.0], [1.0, 1.0, 1.0], ids=["a", "b", "c"])
        assert [d["id"] for d in report.disagreements] == ["b"]
        assert report.disagreements[0]["judge_verdict"] == "fail"
        assert report.disagreements[0]["human_verdict"] == "pass"

    def test_small_sample_is_not_gateable_even_when_perfect(self):
        """A 5-case perfect run must not report a green release gate."""
        report = alignment_report([1.0] * 5, [1.0] * 5)
        assert report.kappa == 1.0
        assert report.gateable is False
        assert report.passed is False

    def test_large_perfect_sample_passes(self):
        report = alignment_report([1.0] * 15 + [0.0] * 10, [1.0] * 15 + [0.0] * 10)
        assert report.passed is True
        assert report.kappa >= KAPPA_GATE


class TestReviewSampling:
    def _records(self, n_pass=40, n_fail=6):
        return [
            {"id": f"p{i}", "score": 0.9, "pass_mark": 0.6, "context": "c", "answer": "a"}
            for i in range(n_pass)
        ] + [
            {"id": f"f{i}", "score": 0.2, "pass_mark": 0.6, "context": "c", "answer": "a"}
            for i in range(n_fail)
        ]

    def test_sample_is_stratified_across_both_verdicts(self):
        """A uniform 5% of an imbalanced set contains almost no failures, and a
        sample with no failures cannot say how the judge handles failures."""
        sample = sample_for_review(self._records(), rate=0.05)
        failures = [r for r in sample if r["score"] < r["pass_mark"]]
        assert failures, "no failed cases drawn"
        assert len(sample) >= 20

    def test_sampling_is_deterministic(self):
        records = self._records()
        assert [r["id"] for r in sample_for_review(records)] == [
            r["id"] for r in sample_for_review(records)
        ]

    def test_low_confidence_cases_are_always_included(self):
        records = self._records(n_pass=40, n_fail=2)
        records[0]["low_confidence"] = True
        records[0]["id"] = "flagged"
        sample = sample_for_review(records, rate=0.01)
        assert any(r["id"] == "flagged" for r in sample)

    def test_sample_never_exceeds_the_population(self):
        sample = sample_for_review(self._records(n_pass=3, n_fail=1), rate=0.5)
        assert len(sample) <= 4

    def test_review_file_hides_the_judge_score(self, tmp_path):
        """Showing the judge's score anchors the reviewer, and a suggestible
        reviewer produces a kappa that measures suggestibility."""
        path = tmp_path / "review.jsonl"
        write_review_queue([{"id": "x", "context": "ctx", "answer": "ans", "score": 0.93}], path)
        row = json.loads(path.read_text(encoding="utf-8").strip())
        assert row["human_score"] is None
        assert "score" not in row

    def test_round_trip_skips_unreviewed_rows(self, tmp_path):
        path = tmp_path / "review.jsonl"
        path.write_text(
            '{"id": "a", "human_score": 1.0}\n'
            '{"id": "b", "human_score": null}\n'
            "\n"
            '{"id": "c", "human_score": 0.0}\n',
            encoding="utf-8",
        )
        assert load_review_queue(path) == {"a": 1.0, "c": 0.0}


# ── Judge parsing ──────────────────────────────────────────────


class _StubLLM:
    """Returns a fixed response, so the judge's own logic is what is tested."""

    def __init__(self, response: str):
        self.response = response

    def complete(self, prompt, **kwargs):
        return self.response


class TestVerdictParsing:
    def test_structured_output_is_decomposed(self):
        raw = (
            "<quotes>价格区间: 20,000~30,000</quotes>"
            "<reasoning>回复中的价格与上下文一致。</reasoning>"
            "<score>5</score>"
        )
        verdict = parse_verdict(raw, JudgeMode.STRUCTURED)
        assert verdict.score == 5.0
        assert verdict.normalised == 1.0
        assert verdict.has_evidence
        assert verdict.format_ok

    def test_missing_tags_flag_format_failure_not_a_zero(self):
        """Regression: treating a format failure as score 0 marked 30% of the
        faithful half as hallucinated (docs/record.md #42)."""
        verdict = parse_verdict("The answer looks accurate to me.", JudgeMode.STRUCTURED)
        assert verdict.format_ok is False

    def test_explicit_no_evidence_is_a_verdict_not_a_format_failure(self):
        verdict = parse_verdict(
            "<quotes>无</quotes><reasoning>上下文未提及。</reasoning><score>0</score>",
            JudgeMode.STRUCTURED,
        )
        assert verdict.format_ok is True
        assert verdict.has_evidence is False
        assert verdict.score == 0.0

    def test_inconsistent_verdict_is_flagged_not_zeroed(self):
        """quotes='无' with a high score is a contradiction. Zeroing it caused
        a 25% false-alarm rate; flagging routes it to a human instead."""
        raw = "<quotes>无</quotes><reasoning>看起来没问题。</reasoning><score>4</score>"
        judge = StructuredJudge(_StubLLM(raw), mode=JudgeMode.STRUCTURED, consensus=False)
        verdict = judge.judge("车型: 秦PLUS", "为您推荐秦PLUS。")
        assert verdict.low_confidence is True
        assert verdict.score == 4.0  # not inverted to 0

    def test_transport_error_is_a_format_failure_not_a_zero(self):
        """A call that never returned produced no verdict. Counting it as a
        score of 0 records a network blip as a detected hallucination."""

        class _DeadLLM:
            def complete(self, prompt, **kwargs):
                raise ConnectionError("Connection reset by peer")

        judge = StructuredJudge(_DeadLLM(), mode=JudgeMode.STRUCTURED, consensus=False)
        verdict = judge.judge("车型: 秦PLUS", "为您推荐秦PLUS。")
        assert verdict.format_ok is False
        assert "Connection reset" in verdict.error

    def test_fabricated_evidence_zeroes_the_verdict(self):
        """Inventing a quote and scoring against it performs the ritual and
        skips the point — that verdict is worth nothing."""
        raw = (
            "<quotes>整车质保为 3 年或 10 万公里</quotes>"
            "<reasoning>与上下文一致。</reasoning><score>5</score>"
        )
        judge = StructuredJudge(_StubLLM(raw), mode=JudgeMode.STRUCTURED, consensus=False)
        verdict = judge.judge("车型: 秦PLUS\n价格区间: 100,000~200,000", "为您推荐秦PLUS。")
        assert verdict.score == 0.0
        assert "fabricated" in verdict.error


class TestQuoteVerification:
    def test_quotes_present_in_context_verify(self):
        context = "车型: 秦PLUS\n价格区间: 100,000~200,000"
        result = verify_quotes(["价格区间: 100,000~200,000"], context)
        assert result["fabricated"] == []
        assert result["grounded_ratio"] == 1.0

    def test_invented_quotes_are_caught(self):
        """A judge citing evidence that is not in the context is hallucinating
        its own justification — the failure mode evidence was meant to close."""
        context = "车型: 秦PLUS\n价格区间: 100,000~200,000"
        result = verify_quotes(["整车质保为 3 年或 10 万公里"], context)
        assert result["fabricated"]

    def test_whitespace_and_punctuation_differences_still_verify(self):
        context = "价格区间: 100,000 ~ 200,000"
        assert not verify_quotes(["价格区间：100,000~200,000"], context)["fabricated"]

    def test_no_quotes_is_neither_verified_nor_fabricated(self):
        result = verify_quotes([], "some context")
        assert result["fabricated"] == []
        assert result["n"] == 0
        assert result["grounded_ratio"] == 0.0


# ── Batch packaging ────────────────────────────────────────────


class _Case:
    def __init__(self, cid, context="ctx", answer="ans"):
        self.id = cid
        self.context = context
        self.answer = answer


class TestBatchPackaging:
    def test_jsonl_carries_custom_id_per_line(self, tmp_path):
        requests = [
            BatchRequest(custom_id=f"c{i}", model="m", messages=[{"role": "user", "content": "x"}])
            for i in range(3)
        ]
        parts = write_batch(requests, tmp_path / "batch.jsonl")
        assert len(parts) == 1
        lines = parts[0].read_text(encoding="utf-8").strip().split("\n")
        assert [json.loads(line)["custom_id"] for line in lines] == ["c0", "c1", "c2"]

    def test_duplicate_ids_rejected(self, tmp_path):
        """Duplicates make the response join ambiguous with no error anywhere."""
        requests = [
            BatchRequest(custom_id="same", model="m", messages=[{"role": "user", "content": "x"}])
            for _ in range(2)
        ]
        with pytest.raises(ValueError, match="duplicate"):
            write_batch(requests, tmp_path / "batch.jsonl")

    def test_oversized_set_splits_into_parts(self, tmp_path, monkeypatch):
        monkeypatch.setattr("src.eval.batch_api.MAX_REQUESTS_PER_BATCH", 2)
        requests = [
            BatchRequest(custom_id=f"c{i}", model="m", messages=[{"role": "user", "content": "x"}])
            for i in range(5)
        ]
        parts = write_batch(requests, tmp_path / "batch.jsonl")
        assert len(parts) == 3
        total = sum(
            len([line for line in p.read_text(encoding="utf-8").splitlines() if line])
            for p in parts
        )
        assert total == 5

    def test_byte_ceiling_is_enforced_independently_of_count(self, tmp_path, monkeypatch):
        """A set well under the request cap still overruns the file-size limit
        once each prompt carries real retrieved context."""
        monkeypatch.setattr("src.eval.batch_api.MAX_BATCH_BYTES", 500)
        requests = [
            BatchRequest(
                custom_id=f"c{i}", model="m", messages=[{"role": "user", "content": "x" * 200}]
            )
            for i in range(5)
        ]
        parts = write_batch(requests, tmp_path / "batch.jsonl")
        assert len(parts) > 1
        assert all(p.stat().st_size <= MAX_BATCH_BYTES for p in parts)

    def test_results_parse_and_join_by_id(self):
        lines = [
            json.dumps(
                {
                    "custom_id": "c1",
                    "response": {
                        "body": {
                            "choices": [
                                {
                                    "message": {
                                        "content": "<quotes>价格</quotes>"
                                        "<reasoning>一致</reasoning><score>5</score>"
                                    }
                                }
                            ]
                        }
                    },
                }
            )
        ]
        parsed = parse_results(lines)
        assert parsed["n_ok"] == 1
        assert parsed["verdicts"]["c1"].score == 5.0

    def test_failed_request_recorded_not_raised(self):
        lines = [json.dumps({"custom_id": "c1", "error": {"message": "rate limited"}})]
        parsed = parse_results(lines)
        assert parsed["verdicts"] == {}
        assert "c1" in parsed["failures"]

    def test_malformed_response_recorded_not_raised(self):
        lines = [json.dumps({"custom_id": "c1", "response": {"body": {}}})]
        parsed = parse_results(lines)
        assert "c1" in parsed["failures"]

    def test_reconcile_reports_missing_rather_than_scoring_them_zero(self):
        """Treating an unjudged case as a zero marks it as a hallucination."""
        cases = [_Case("c1"), _Case("c2"), _Case("c3")]
        parsed = {"verdicts": {"c1": object()}, "failures": {}}
        result = reconcile(cases, parsed)
        assert result["n_judged"] == 1
        assert result["coverage"] == pytest.approx(1 / 3, abs=1e-4)
        assert set(result["missing"]) == {"c2", "c3"}

    def test_full_coverage_reports_no_missing(self):
        cases = [_Case("c1"), _Case("c2")]
        parsed = {"verdicts": {"c1": object(), "c2": object()}, "failures": {}}
        result = reconcile(cases, parsed)
        assert result["coverage"] == 1.0
        assert result["missing"] == []


# ── Case construction ──────────────────────────────────────────


class TestCaseConstruction:
    def test_pairs_share_a_context_so_only_the_injection_differs(self):
        from src.eval.judge_ab import build_cases

        cases = build_cases(limit=3, difficulty="subtle")
        assert len(cases) == 6
        for i in range(0, 6, 2):
            faithful, halluc = cases[i], cases[i + 1]
            assert faithful.context == halluc.context
            assert halluc.answer.startswith(faithful.answer)
            assert not faithful.hallucinated and halluc.hallucinated

    def test_difficulty_tiers_produce_different_injections(self):
        from src.eval.judge_ab import build_cases

        blatant = {c.answer for c in build_cases(limit=3, difficulty="blatant") if c.hallucinated}
        subtle = {c.answer for c in build_cases(limit=3, difficulty="subtle") if c.hallucinated}
        assert not (blatant & subtle)
