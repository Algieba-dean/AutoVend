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
- cloud unavailable -> fall back to local (quality degrades, service continues)
Neither direction fails the request while any model can answer it.
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
        cloud: Optional[BaseLLM] = None,
        local_tasks: Optional[frozenset] = None,
    ):
        self.local = local
        self.cloud = cloud
        self.local_tasks = local_tasks if local_tasks is not None else LOCAL_TASKS
        self._local_healthy: Optional[bool] = None

    # ── routing ───────────────────────────────────────────────────────

    def backend_for(self, task: Task) -> tuple:
        """
        Resolve (backend, route, fallback) for a task.

        Returns the chosen backend, its Route label for telemetry, and the
        backend to retry with if the first one fails.
        """
        wants_local = task in self.local_tasks

        if wants_local and self._local_available():
            return self.local, Route.LOCAL, self.cloud
        if self.cloud is not None:
            return self.cloud, Route.CLOUD, self.local if self._local_available() else None
        if self.local is not None:
            # No cloud configured: serve everything locally rather than refuse.
            return self.local, Route.LOCAL, None
        raise RuntimeError("HybridRouter has no backend configured.")

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

    def _invoke(self, task: Task, method: str, payload: Any, **kwargs) -> str:
        backend, route, fallback = self.backend_for(task)

        try:
            return self._call(backend, route, task, method, payload, **kwargs)
        except Exception as exc:
            if fallback is None:
                raise
            other = Route.CLOUD if route is Route.LOCAL else Route.LOCAL
            logger.warning(
                f"{route.value} backend failed for {task.value} ({exc}); trying {other.value}"
            )
            if route is Route.LOCAL:
                # Do not keep paying the timeout on a server that is down.
                self._local_healthy = False
            return self._call(fallback, other, task, method, payload, **kwargs)

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
            "cloud": {
                "model": getattr(self.cloud, "model", None),
                "base_url": getattr(self.cloud, "base_url", None),
            }
            if self.cloud
            else None,
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
        local = LLMFactory.create_llm(
            provider="openai",
            api_key=config.local_llm_api_key,
            model=config.local_llm_model,
            base_url=config.local_llm_base_url,
        )

    cloud = LLMFactory.create_llm()
    return HybridRouter(local=local, cloud=cloud)
