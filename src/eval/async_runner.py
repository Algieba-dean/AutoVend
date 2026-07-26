"""
Async evaluation queue.

The judge workload is embarrassingly parallel — every case is independent — but
the naive implementation is a `for` loop, so wall-clock is the sum of every
round trip. With a judge call at ~2s and 500 cases, that is a twenty-minute CI
job spent almost entirely waiting on sockets.

This runs the queue concurrently under `RateLimiter`, which is the part that
makes concurrency safe rather than merely fast: unbounded `asyncio.gather` over
500 tasks opens 500 sockets, and the provider answers with connection resets
rather than clean 429s, which retries do not fix.

Results come back **in submission order** regardless of completion order.
Evaluation output feeds a gate that compares against recorded baselines, and a
report whose row order shifts between runs makes every diff unreadable.
"""

import asyncio
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Sequence

from src.eval.rate_limit import RateLimiter, RateLimits, estimate_tokens
from src.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class TaskResult:
    """One completed evaluation task."""

    index: int
    key: str
    value: Any = None
    error: str = ""
    elapsed_s: float = 0.0

    @property
    def ok(self) -> bool:
        return not self.error


@dataclass
class QueueReport:
    """What the run cost."""

    n_tasks: int
    n_ok: int
    n_failed: int
    wall_seconds: float
    limiter: Dict[str, Any] = field(default_factory=dict)
    results: List[TaskResult] = field(default_factory=list)

    @property
    def throughput(self) -> float:
        return self.n_tasks / self.wall_seconds if self.wall_seconds else 0.0

    @property
    def mean_latency(self) -> float:
        """
        Mean per-call latency.

        Reported alongside wall-clock because it is what separates a real
        concurrency win from provider weather: if the serial and concurrent
        halves disagree on per-call latency, part of the wall-clock difference
        is the provider having a better minute, not the queue.
        """
        done = [r.elapsed_s for r in self.results if r.ok]
        return sum(done) / len(done) if done else 0.0

    def summary(self) -> Dict[str, Any]:
        return {
            "n_tasks": self.n_tasks,
            "n_ok": self.n_ok,
            "n_failed": self.n_failed,
            "wall_seconds": round(self.wall_seconds, 2),
            "mean_latency_s": round(self.mean_latency, 2),
            "tasks_per_second": round(self.throughput, 2),
            "limiter": self.limiter,
        }


@dataclass
class EvalTask:
    """One unit of judged work."""

    key: str
    #: Called with no arguments; may be sync or async.
    fn: Callable[[], Any]
    #: For the TPM bucket. Under-estimating costs a 429, over-estimating costs
    #: throughput, so estimate from the actual prompt where possible.
    estimated_tokens: int = 0


async def run_queue(
    tasks: Sequence[EvalTask],
    limits: Optional[RateLimits] = None,
    on_progress: Optional[Callable[[int, int], None]] = None,
) -> QueueReport:
    """
    Run every task concurrently under the rate limits.

    A task that raises becomes a failed `TaskResult` rather than cancelling its
    siblings: losing 499 completed evaluations because the 500th hit a
    malformed record would be its own kind of failure.
    """
    limiter = RateLimiter(limits=limits)
    results: List[Optional[TaskResult]] = [None] * len(tasks)
    completed = 0
    lock = asyncio.Lock()

    async def run_one(index: int, task: EvalTask) -> None:
        nonlocal completed
        started = time.perf_counter()
        try:
            value = await limiter.call(task.fn, estimated_tokens=task.estimated_tokens)
            result = TaskResult(index=index, key=task.key, value=value)
        except Exception as exc:
            result = TaskResult(index=index, key=task.key, error=str(exc)[:200])
            logger.warning(f"task {task.key} failed: {str(exc)[:160]}")
        result.elapsed_s = time.perf_counter() - started
        results[index] = result

        async with lock:
            completed += 1
            if on_progress:
                on_progress(completed, len(tasks))

    started = time.perf_counter()
    await asyncio.gather(*(run_one(i, t) for i, t in enumerate(tasks)))
    wall = time.perf_counter() - started

    ordered = [r for r in results if r is not None]
    return QueueReport(
        n_tasks=len(tasks),
        n_ok=sum(1 for r in ordered if r.ok),
        n_failed=sum(1 for r in ordered if not r.ok),
        wall_seconds=wall,
        limiter=limiter.stats.as_dict(),
        results=ordered,
    )


def run_queue_sync(
    tasks: Sequence[EvalTask],
    limits: Optional[RateLimits] = None,
    on_progress: Optional[Callable[[int, int], None]] = None,
) -> QueueReport:
    """Blocking entry point, for CLIs and tests."""
    return asyncio.run(run_queue(tasks, limits=limits, on_progress=on_progress))


def run_serial(tasks: Sequence[EvalTask]) -> QueueReport:
    """
    Run the same tasks one at a time.

    Exists to make the concurrency claim measurable rather than asserted: the
    speed-up is only meaningful against the same tasks on the same machine
    against the same provider, minutes apart.
    """
    results: List[TaskResult] = []
    started = time.perf_counter()

    for index, task in enumerate(tasks):
        task_started = time.perf_counter()
        try:
            value = task.fn()
            result = TaskResult(index=index, key=task.key, value=value)
        except Exception as exc:
            result = TaskResult(index=index, key=task.key, error=str(exc)[:200])
        result.elapsed_s = time.perf_counter() - task_started
        results.append(result)

    wall = time.perf_counter() - started
    return QueueReport(
        n_tasks=len(tasks),
        n_ok=sum(1 for r in results if r.ok),
        n_failed=sum(1 for r in results if not r.ok),
        wall_seconds=wall,
        limiter={},
        results=results,
    )


def judge_tasks(judge, cases: Sequence[Any]) -> List[EvalTask]:
    """Wrap judge cases as queue tasks, sized for the token bucket."""
    return [
        EvalTask(
            key=case.id,
            fn=(lambda c=case: judge.judge(c.context, c.answer)),
            estimated_tokens=estimate_tokens(case.context + case.answer) + 400,
        )
        for case in cases
    ]
