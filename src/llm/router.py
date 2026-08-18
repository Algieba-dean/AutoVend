"""
Hybrid inference router: local vLLM for the control path, cloud API for synthesis.

The two kinds of LLM work in this system have very different shapes:

**Control path** — parsing a query into filter conditions, filling a Pydantic
schema from a transcript, deciding what is still missing. Short prompts, short
JSON outputs, a fixed vocabulary, and one or more calls on *every* turn. These
are latency-critical and volume-heavy, and an 8B model handles them because the
output space is constrained by the schema rather than by the model's judgement.

**Synthesis path** — comparing five vehicles against a customer's stated and
inferred needs and writing the recommendation. Long context, open-ended output,
and the part a customer actually reads. Quality dominates; it goes to the cloud.

Routing on that distinction is what makes the split defensible: it is not
"cheap model for cheap work", it is "constrained output stays local, open-ended
generation does not".

Both backends speak the OpenAI protocol, so `OpenAILLM` serves both and the
router only decides *which endpoint*, never *how to call it*.

Failure handling is asymmetric on purpose:
- local unavailable -> fall back to cloud (correctness preserved, cost rises)
- cloud unavailable -> try the next cloud provider, then local (quality
  degrades, service continues)
Neither direction fails the request while any model can answer it.

The cloud side is an ordered chain rather than a single endpoint because free
tiers exhaust their daily token budget mid-session; losing the synthesis path
halfway through a conversation is worse than switching model vendors.
"""

from enum import Enum
from typing import Any, Dict, List, Optional

from src.llm.base_llm import BaseLLM
from src.llm.telemetry import Route, telemetry
from src.utils.config import config
from src.utils.logger import get_logger

logger = get_logger(__name__)


class Task(str, Enum):
    """
    What a call is for. The router maps tasks to backends, so adding a call
    site means classifying it once here rather than picking a model inline.

    The granularity is deliberately coarse — three buckets that route
    differently, not one entry per call site. Splitting `EXTRACTION` into
    profile/needs/reservation would triple the enum without changing a single
    routing decision.
    """

    # Control path — schema-constrained, high frequency.
    QUERY_PARSE = "query_parse"  # natural language -> filter conditions
    EXTRACTION = "extraction"  # transcript -> Pydantic schema

    # Synthesis path — open-ended, customer-facing.
    RESPONSE_GENERATION = "response_generation"

    # Evaluation — judged offline, always cloud so the judge is the stronger model.
    JUDGE = "judge"


#: Tasks served locally when a local backend is up. Everything else goes cloud.
LOCAL_TASKS = frozenset({Task.QUERY_PARSE, Task.EXTRACTION})


class HybridRouter:
    """
    Routes LLM calls between a local vLLM server and a cloud API.

    Stateless apart from the backends themselves; safe to share across requests.
    """

    def __init__(
        self,
        local: Optional[BaseLLM] = None,
        cloud: Optional[Any] = None,
        local_tasks: Optional[frozenset] = None,
    ):
        """
        Args:
            local: Local inference backend, or None.
            cloud: A single cloud backend or an ordered list of them; earlier
                entries are preferred and later ones act as quota/outage
                fallbacks.
            local_tasks: Override which tasks route local.
        """
        self.local = local
        if cloud is None:
            self.cloud_chain: List[BaseLLM] = []
        elif isinstance(cloud, (list, tuple)):
            self.cloud_chain = [c for c in cloud if c is not None]
        else:
            self.cloud_chain = [cloud]
        self.local_tasks = local_tasks if local_tasks is not None else LOCAL_TASKS
        self._local_healthy: Optional[bool] = None

    @property
    def cloud(self) -> Optional[BaseLLM]:
        """The preferred cloud backend, or None when no cloud is configured."""
        return self.cloud_chain[0] if self.cloud_chain else None

    # ── routing ───────────────────────────────────────────────────────

    def plan_for(self, task: Task) -> List[tuple]:
        """
        Ordered (backend, route) attempts for a task, best first.

        Returning the whole plan rather than a single choice plus one fallback
        is what lets a request survive both a dead local server and an
        exhausted cloud quota in the same turn.
        """
        wants_local = task in self.local_tasks
        local_available = self._local_available()

        plan: List[tuple] = []
        if wants_local and local_available:
            plan.append((self.local, Route.LOCAL))
        plan.extend((backend, Route.CLOUD) for backend in self.cloud_chain)
        if not wants_local and local_available:
            # Last resort for synthesis: a weaker local answer beats no answer.
            plan.append((self.local, Route.LOCAL))

        if not plan:
            if self.local is not None:
                # Local configured but unhealthy, and no cloud at all — try it
                # anyway rather than refuse outright.
                return [(self.local, Route.LOCAL)]
            raise RuntimeError("HybridRouter has no backend configured.")
        return plan

    def backend_for(self, task: Task) -> tuple:
        """
        Resolve (backend, route, fallback) for a task.

        Kept for callers that only need the preferred backend (health display,
        model-name lookup). `plan_for` is what invocation uses.
        """
        plan = self.plan_for(task)
        backend, route = plan[0]
        fallback = plan[1][0] if len(plan) > 1 else None
        return backend, route, fallback

    def _local_available(self) -> bool:
        """
        Health-check the local server once, then remember the answer.

        Probing on every call would add a round trip to the very path the local
        model exists to make fast. Call `reset_health()` after starting or
        stopping the server.
        """
        if self.local is None:
            return False
        if self._local_healthy is None:
            try:
                self._local_healthy = bool(self.local.is_available())
            except Exception as exc:
                logger.warning(f"Local LLM health check failed: {exc}")
                self._local_healthy = False
            logger.info(
                f"Local LLM {'available' if self._local_healthy else 'unavailable'} — "
                f"control-path calls will go {'local' if self._local_healthy else 'to the cloud'}"
            )
        return self._local_healthy

    def reset_health(self) -> None:
        """Forget the cached health verdict (after the server starts or stops)."""
        self._local_healthy = None

    # ── invocation ────────────────────────────────────────────────────

    def complete(self, task: Task, prompt: str, **kwargs) -> str:
        """Run a completion for `task` on whichever backend it routes to."""
        return self._invoke(task, "complete", prompt, **kwargs)

    def chat(self, task: Task, messages: List[Dict[str, str]], **kwargs) -> str:
        """Run a chat completion for `task`."""
        return self._invoke(task, "chat", messages, **kwargs)

    def stream_chat(self, task: Task, messages: List[Dict[str, str]], **kwargs):
        """Stream token chunks for `task` dynamically."""
        plan = self.plan_for(task)
        last_error: Optional[Exception] = None

        for index, (backend, route) in enumerate(plan):
            try:
                if hasattr(backend, "chat_stream_tokens"):
                    yield from backend.chat_stream_tokens(messages, **kwargs)
                    return
                else:
                    text = self._call(backend, route, task, "chat", messages, **kwargs)
                    yield text
                    return
            except Exception as exc:
                last_error = exc
                model = getattr(backend, "model", "?")
                remaining = len(plan) - index - 1
                logger.warning(
                    f"{route.value} backend '{model}' failed during stream_chat for {task.value} ({exc}); "
                    + (f"{remaining} fallback(s) left" if remaining else "no fallbacks left")
                )
                if route is Route.LOCAL:
                    self._local_healthy = False

        if last_error:
            raise last_error

    def _invoke(self, task: Task, method: str, payload: Any, **kwargs) -> str:
        plan = self.plan_for(task)
        last_error: Optional[Exception] = None

        for index, (backend, route) in enumerate(plan):
            try:
                return self._call(backend, route, task, method, payload, **kwargs)
            except Exception as exc:
                last_error = exc
                model = getattr(backend, "model", "?")
                remaining = len(plan) - index - 1
                logger.warning(
                    f"{route.value} backend '{model}' failed for {task.value} ({exc}); "
                    + (f"{remaining} fallback(s) left" if remaining else "no fallbacks left")
                )
                if route is Route.LOCAL:
                    # Do not keep paying the timeout on a server that is down.
                    self._local_healthy = False

        raise last_error if last_error else RuntimeError("No backend produced a result.")

    def _call(self, backend: BaseLLM, route: Route, task: Task, method: str, payload, **kwargs):
        model = getattr(backend, "model", "unknown")
        with telemetry.measure(task.value, route, model) as record:
            result = getattr(backend, method)(payload, **kwargs)
            usage = getattr(backend, "last_usage", None)
            if usage:
                record.prompt_tokens = usage.get("prompt_tokens", 0)
                record.completion_tokens = usage.get("completion_tokens", 0)
            record.ttft_s = getattr(backend, "last_ttft_s", None)
            return result

    def bind(self, task: Task) -> "TaskBoundLLM":
        """
        View the router as a plain LLM for one task.

        Lets duck-typed consumers such as `LLMParser` stay unaware that routing
        exists — they keep calling `.chat()` on something that looks like a
        `BaseLLM`.
        """
        return TaskBoundLLM(self, task)

    def describe(self) -> Dict[str, Any]:
        """Human-readable view of the current routing setup, for /health."""
        return {
            "local": {
                "model": getattr(self.local, "model", None),
                "base_url": getattr(self.local, "base_url", None),
                "available": self._local_available(),
            }
            if self.local
            else None,
            # Ordered: the first entry is preferred, the rest are quota/outage
            # fallbacks.
            "cloud_chain": [
                {
                    "model": getattr(backend, "model", None),
                    "base_url": getattr(backend, "base_url", None),
                }
                for backend in self.cloud_chain
            ],
            "local_tasks": sorted(t.value for t in self.local_tasks),
        }


class TaskBoundLLM:
    """
    A `BaseLLM`-shaped view of the router with the task fixed.

    Not a `BaseLLM` subclass on purpose: it has no endpoint or credentials of
    its own, and inheriting would imply it does.
    """

    def __init__(self, router: HybridRouter, task: Task):
        self._router = router
        self._task = task

    @property
    def model(self) -> str:
        backend, _, _ = self._router.backend_for(self._task)
        return getattr(backend, "model", "unknown")

    @property
    def base_url(self) -> Optional[str]:
        backend, _, _ = self._router.backend_for(self._task)
        return getattr(backend, "base_url", None)

    def complete(self, prompt: str, **kwargs) -> str:
        return self._router.complete(self._task, prompt, **kwargs)

    def chat(self, messages: List[Dict[str, str]], **kwargs) -> str:
        return self._router.chat(self._task, messages, **kwargs)

    def is_available(self) -> bool:
        try:
            backend, _, _ = self._router.backend_for(self._task)
        except RuntimeError:
            return False
        return bool(backend and backend.is_available())


def build_default_router() -> HybridRouter:
    """
    Assemble the router from configuration.

    Falls back gracefully: no local server configured means everything goes
    cloud; no cloud credentials means everything that can run locally does, and
    the rest uses the mock backend so the app still boots.
    """
    from src.llm.factory import LLMFactory

    local = None
    if config.local_llm_base_url:
        from src.llm.openai_llm import extra_body_for_local

        local = LLMFactory.create_llm(
            provider="openai",
            api_key=config.local_llm_api_key,
            model=config.local_llm_model,
            base_url=config.local_llm_base_url,
            # Suppress reasoning-model chain-of-thought on the control path.
            extra_body=extra_body_for_local(),
        )

    cloud_chain = []
    if config.llm_api_key:
        cloud_chain.append(LLMFactory.create_llm())
    if config.deepseek_api_key:
        cloud_chain.append(
            LLMFactory.create_llm(
                provider="openai",
                api_key=config.deepseek_api_key,
                model=config.deepseek_model,
                base_url=config.deepseek_base_url,
            )
        )
    if not cloud_chain:
        # Keeps the mock backend reachable so the app still boots keyless.
        cloud_chain.append(LLMFactory.create_llm())

    return HybridRouter(local=local, cloud=cloud_chain)
