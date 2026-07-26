"""
Tests for judge selection in the RAGAS evaluation.

RAGAS issues several calls per sample, so starting a run against a provider
that is already near its daily cap loses the whole run — which is how the first
attempt at this was wasted. `resolve_judge` probes before committing.
"""

import pytest

from src.eval import ragas_eval


class _StubBackend:
    def __init__(self, model, fail=False):
        self.model = model
        self.api_key = f"key-{model}"
        self.base_url = f"https://{model}/v1"
        self.fail = fail
        self.probes = 0

    def complete(self, prompt, **kwargs):
        self.probes += 1
        if self.fail:
            raise RuntimeError(f"{self.model}: rate_limit_exceeded")
        return "pong"


class _StubRouter:
    def __init__(self, *backends):
        self.cloud_chain = list(backends)


@pytest.fixture
def router(monkeypatch):
    """Install a stub router factory and hand back a setter for its chain."""

    def install(*backends):
        stub = _StubRouter(*backends)
        monkeypatch.setattr("src.llm.router.build_default_router", lambda: stub, raising=True)
        return stub

    return install


class TestResolveJudge:
    def test_picks_the_first_provider_with_quota(self, router):
        primary, secondary = _StubBackend("groq"), _StubBackend("deepseek")
        router(primary, secondary)

        judge = ragas_eval.resolve_judge()

        assert judge["model"] == "groq"
        assert secondary.probes == 0, "a healthy primary must not cost a second probe"

    def test_skips_a_rate_limited_provider(self, router):
        primary, secondary = _StubBackend("groq", fail=True), _StubBackend("deepseek")
        router(primary, secondary)

        judge = ragas_eval.resolve_judge()

        assert judge["model"] == "deepseek"
        assert primary.probes == 1, "the primary must be probed, not assumed dead"

    def test_probe_happens_before_the_run(self, router):
        """The whole point: fail in one call, not twenty minutes in."""
        backend = _StubBackend("deepseek")
        router(backend)

        ragas_eval.resolve_judge()

        assert backend.probes == 1

    def test_preference_selects_by_substring(self, router):
        router(_StubBackend("groq"), _StubBackend("deepseek-v4-flash"))

        assert ragas_eval.resolve_judge("deepseek")["model"] == "deepseek-v4-flash"

    def test_unknown_preference_exits(self, router):
        router(_StubBackend("groq"))

        with pytest.raises(SystemExit, match="No cloud provider matches"):
            ragas_eval.resolve_judge("anthropic")

    def test_all_providers_exhausted_exits(self, router):
        router(_StubBackend("groq", fail=True), _StubBackend("deepseek", fail=True))

        with pytest.raises(SystemExit, match="failed a probe"):
            ragas_eval.resolve_judge()

    def test_returns_the_credentials_the_client_needs(self, router):
        router(_StubBackend("deepseek"))

        judge = ragas_eval.resolve_judge()

        assert set(judge) == {"model", "api_key", "base_url"}


class TestSummarize:
    """
    RAGAS records NaN for a failed job and its own aggregate treats that as
    0.0, so a rate-limited run reports a confident-looking zero. These assert
    the split between "scored badly" and "not measured".
    """

    class _FakeResult:
        def __init__(self, frame):
            self._frame = frame

        def to_pandas(self):
            return self._frame

    def test_averages_only_successful_samples(self):
        pd = pytest.importorskip("pandas")
        frame = pd.DataFrame(
            {
                "user_input": ["a", "b", "c"],
                "faithfulness": [1.0, 0.0, float("nan")],
            }
        )

        summary = ragas_eval.summarize(self._FakeResult(frame))

        assert summary["faithfulness"]["score"] == pytest.approx(0.5)
        assert summary["faithfulness"]["n_scored"] == 2
        assert summary["faithfulness"]["n_failed"] == 1

    def test_all_failed_yields_none_not_zero(self):
        pd = pytest.importorskip("pandas")
        frame = pd.DataFrame({"user_input": ["a"], "faithfulness": [float("nan")]})

        summary = ragas_eval.summarize(self._FakeResult(frame))

        assert summary["faithfulness"]["score"] is None, (
            "a total failure must not be reported as a score of 0.0"
        )

    def test_ignores_the_dataset_columns(self):
        pd = pytest.importorskip("pandas")
        frame = pd.DataFrame(
            {
                "user_input": ["a"],
                "retrieved_contexts": [["ctx"]],
                "response": ["text"],
                "reference": ["ref"],
                "faithfulness": [1.0],
            }
        )

        assert set(ragas_eval.summarize(self._FakeResult(frame))) == {"faithfulness"}
