"""
Tests for the hybrid inference router and its telemetry.

The routing policy is the deliverable here: control-path tasks go local,
synthesis goes cloud, and failure in either direction degrades to the other
side instead of failing the request. Each of those claims gets a test, because
each is the kind of thing that silently rots when a refactor touches it.
"""

import pytest

from src.llm.router import LOCAL_TASKS, HybridRouter, Task, TaskBoundLLM
from src.llm.telemetry import CallRecord, Route, TelemetryCollector


class _StubLLM:
    """BaseLLM-shaped stub that records calls and can be made to fail."""

    def __init__(self, name, available=True, fail=False):
        self.model = name
        self.base_url = f"http://{name}"
        self.available = available
        self.fail = fail
        self.calls = []
        self.last_usage = {"prompt_tokens": 10, "completion_tokens": 5}
        self.last_ttft_s = 0.05

    def complete(self, prompt, **kwargs):
        self.calls.append(("complete", prompt))
        if self.fail:
            raise RuntimeError(f"{self.model} is down")
        return f"{self.model}:{prompt}"

    def chat(self, messages, **kwargs):
        self.calls.append(("chat", messages))
        if self.fail:
            raise RuntimeError(f"{self.model} is down")
        return f"{self.model}:chat"

    def is_available(self):
        return self.available


@pytest.fixture
def local():
    return _StubLLM("local-llama")


@pytest.fixture
def cloud():
    return _StubLLM("groq-70b")


class TestRoutingPolicy:
    def test_control_path_tasks_go_local(self, local, cloud):
        router = HybridRouter(local=local, cloud=cloud)

        for task in LOCAL_TASKS:
            backend, route, _ = router.backend_for(task)
            assert backend is local, f"{task.value} should be served locally"
            assert route is Route.LOCAL

    def test_synthesis_and_judging_go_cloud(self, local, cloud):
        router = HybridRouter(local=local, cloud=cloud)

        for task in (Task.RESPONSE_GENERATION, Task.JUDGE):
            backend, route, _ = router.backend_for(task)
            assert backend is cloud, f"{task.value} should be served by the cloud"
            assert route is Route.CLOUD

    def test_everything_goes_cloud_when_local_is_down(self, cloud):
        router = HybridRouter(local=_StubLLM("local", available=False), cloud=cloud)

        backend, route, _ = router.backend_for(Task.EXTRACTION)

        assert backend is cloud
        assert route is Route.CLOUD

    def test_everything_goes_cloud_when_no_local_is_configured(self, cloud):
        router = HybridRouter(local=None, cloud=cloud)

        backend, _, fallback = router.backend_for(Task.QUERY_PARSE)

        assert backend is cloud
        assert fallback is None

    def test_everything_goes_local_when_no_cloud_is_configured(self, local):
        router = HybridRouter(local=local, cloud=None)

        backend, route, _ = router.backend_for(Task.RESPONSE_GENERATION)

        assert backend is local
        assert route is Route.LOCAL

    def test_no_backends_at_all_raises(self):
        with pytest.raises(RuntimeError, match="no backend"):
            HybridRouter().backend_for(Task.EXTRACTION)

    def test_health_check_runs_once(self, cloud):
        """The check must not add a round trip to every control-path call."""
        probe_count = 0

        class _Probed(_StubLLM):
            def is_available(self):
                nonlocal probe_count
                probe_count += 1
                return True

        router = HybridRouter(local=_Probed("local"), cloud=cloud)
        for _ in range(5):
            router.backend_for(Task.EXTRACTION)

        assert probe_count == 1

    def test_reset_health_reprobes(self, cloud):
        local = _StubLLM("local", available=False)
        router = HybridRouter(local=local, cloud=cloud)
        assert router.backend_for(Task.EXTRACTION)[0] is cloud

        local.available = True  # the server came up
        router.reset_health()

        assert router.backend_for(Task.EXTRACTION)[0] is local


class TestFallback:
    def test_local_failure_falls_back_to_cloud(self, cloud):
        local = _StubLLM("local", fail=True)
        router = HybridRouter(local=local, cloud=cloud)

        result = router.complete(Task.EXTRACTION, "extract this")

        assert result == "groq-70b:extract this"
        assert local.calls, "local must have been tried first"

    def test_local_failure_marks_local_unhealthy(self, cloud):
        """One failed call must not condemn every later call to the same timeout."""
        local = _StubLLM("local", fail=True)
        router = HybridRouter(local=local, cloud=cloud)

        router.complete(Task.EXTRACTION, "first")
        router.complete(Task.EXTRACTION, "second")

        assert len(local.calls) == 1, "second call should skip the dead local server"

    def test_cloud_failure_falls_back_to_local(self, local):
        cloud = _StubLLM("cloud", fail=True)
        router = HybridRouter(local=local, cloud=cloud)

        result = router.complete(Task.RESPONSE_GENERATION, "write the reply")

        assert result == "local-llama:write the reply"

    def test_failure_with_no_fallback_raises(self):
        router = HybridRouter(local=None, cloud=_StubLLM("cloud", fail=True))

        with pytest.raises(RuntimeError, match="cloud is down"):
            router.complete(Task.RESPONSE_GENERATION, "x")


class TestCloudChain:
    """
    A second cloud provider covers the case that actually bit in practice: a
    free tier exhausting its daily token budget mid-conversation.
    """

    def test_prefers_the_first_provider(self):
        primary, secondary = _StubLLM("groq"), _StubLLM("deepseek")
        router = HybridRouter(cloud=[primary, secondary])

        assert router.complete(Task.RESPONSE_GENERATION, "x") == "groq:x"
        assert not secondary.calls

    def test_falls_through_to_the_second_provider(self):
        primary, secondary = _StubLLM("groq", fail=True), _StubLLM("deepseek")
        router = HybridRouter(cloud=[primary, secondary])

        assert router.complete(Task.RESPONSE_GENERATION, "x") == "deepseek:x"
        assert primary.calls, "the primary must be attempted first"

    def test_falls_through_to_local_after_every_cloud_fails(self, local):
        router = HybridRouter(
            local=local, cloud=[_StubLLM("groq", fail=True), _StubLLM("deepseek", fail=True)]
        )

        assert router.complete(Task.RESPONSE_GENERATION, "x") == "local-llama:x"

    def test_control_path_still_prefers_local_over_the_chain(self, local):
        primary = _StubLLM("groq")
        router = HybridRouter(local=local, cloud=[primary, _StubLLM("deepseek")])

        router.complete(Task.EXTRACTION, "x")

        assert local.calls
        assert not primary.calls

    def test_raises_the_last_error_when_everything_fails(self):
        router = HybridRouter(cloud=[_StubLLM("groq", fail=True), _StubLLM("deepseek", fail=True)])

        with pytest.raises(RuntimeError, match="deepseek is down"):
            router.complete(Task.RESPONSE_GENERATION, "x")

    def test_single_backend_is_accepted_as_a_bare_value(self, cloud):
        """Callers that pass one backend must not have to wrap it in a list."""
        router = HybridRouter(cloud=cloud)

        assert router.cloud is cloud
        assert router.cloud_chain == [cloud]

    def test_describe_lists_the_chain_in_order(self):
        primary, secondary = _StubLLM("groq"), _StubLLM("deepseek")

        described = HybridRouter(cloud=[primary, secondary]).describe()

        assert [c["model"] for c in described["cloud_chain"]] == ["groq", "deepseek"]


class TestTaskBoundLLM:
    def test_quacks_like_a_base_llm(self, local, cloud):
        bound = HybridRouter(local=local, cloud=cloud).bind(Task.QUERY_PARSE)

        assert isinstance(bound, TaskBoundLLM)
        assert bound.model == "local-llama"
        assert bound.is_available()
        assert bound.chat([{"role": "user", "content": "hi"}]) == "local-llama:chat"

    def test_routes_through_the_router(self, local, cloud):
        router = HybridRouter(local=local, cloud=cloud)

        router.bind(Task.QUERY_PARSE).complete("parse")
        router.bind(Task.RESPONSE_GENERATION).complete("write")

        assert ("complete", "parse") in local.calls
        assert ("complete", "write") in cloud.calls


class TestTelemetry:
    def test_records_route_tokens_and_ttft(self, local, cloud):
        collector = TelemetryCollector()
        router = HybridRouter(local=local, cloud=cloud)

        import src.llm.router as router_module

        original = router_module.telemetry
        router_module.telemetry = collector
        try:
            router.complete(Task.EXTRACTION, "x")
            router.complete(Task.RESPONSE_GENERATION, "y")
        finally:
            router_module.telemetry = original

        by_task = {r.task: r for r in collector.records}
        assert by_task["extraction"].route is Route.LOCAL
        assert by_task["response_generation"].route is Route.CLOUD
        assert by_task["extraction"].prompt_tokens == 10
        assert by_task["extraction"].ttft_s == 0.05

    def test_failed_calls_are_recorded_as_failed(self):
        collector = TelemetryCollector()

        with pytest.raises(ValueError):
            with collector.measure("t", Route.LOCAL, "m"):
                raise ValueError("boom")

        assert len(collector.records) == 1
        assert not collector.records[0].ok
        assert "boom" in collector.records[0].error

    def test_cost_uses_cloud_pricing_only_for_cloud_calls(self):
        local_call = CallRecord(
            task="extraction",
            route=Route.LOCAL,
            model="m",
            latency_s=0.1,
            prompt_tokens=1_000_000,
            completion_tokens=1_000_000,
        )
        cloud_call = CallRecord(
            task="generation",
            route=Route.CLOUD,
            model="m",
            latency_s=0.1,
            prompt_tokens=1_000_000,
            completion_tokens=1_000_000,
        )

        assert local_call.cost_usd == 0.0
        assert cloud_call.cost_usd == pytest.approx(0.59 + 0.79)

    def test_savings_compare_against_the_all_cloud_counterfactual(self):
        collector = TelemetryCollector()
        collector.record(
            CallRecord(
                task="extraction",
                route=Route.LOCAL,
                model="m",
                latency_s=0.1,
                prompt_tokens=1_000_000,
                completion_tokens=0,
            )
        )
        collector.record(
            CallRecord(
                task="generation",
                route=Route.CLOUD,
                model="m",
                latency_s=0.1,
                prompt_tokens=1_000_000,
                completion_tokens=0,
            )
        )

        cost = collector.cost_breakdown()

        assert cost["actual_usd"] == pytest.approx(0.59)
        assert cost["all_cloud_usd"] == pytest.approx(1.18)
        assert cost["saved_pct"] == pytest.approx(50.0)

    def test_summary_breaks_down_by_route_and_task(self):
        collector = TelemetryCollector()
        for task, route in [("a", Route.LOCAL), ("a", Route.LOCAL), ("b", Route.CLOUD)]:
            collector.record(
                CallRecord(task=task, route=route, model="m", latency_s=0.1, ttft_s=0.02)
            )

        summary = collector.summary()

        assert summary["n_calls"] == 3
        assert summary["by_route"]["local"]["n_calls"] == 2
        assert summary["by_task"]["b"]["n_calls"] == 1
        assert "ttft_p95_s" in summary["overall"]

    def test_empty_summary_is_well_formed(self):
        assert TelemetryCollector().summary() == {"n_calls": 0, "by_route": {}, "by_task": {}}
