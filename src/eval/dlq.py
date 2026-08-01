"""
Checkpointing and Dead Letter Queue (DLQ) Manager for Evaluation Tasks.

Provides:
1. Checkpointing: Persists finished evaluation task results so interrupted runs can resume
   without re-executing already completed tasks.
2. Dead Letter Queue (DLQ): Captures failed task items to a persistent DLQ file.
3. Precision Retry: Enables retrying *only* failed items in the DLQ, merging retried
   successes back into the primary checkpoint and results record.
"""

import json
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

from src.eval.async_runner import EvalTask, QueueReport, TaskResult, run_queue
from src.eval.rate_limit import RateLimits
from src.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class DLQItem:
    """One failed evaluation item in the Dead Letter Queue."""

    key: str
    error: str
    timestamp: float = field(default_factory=time.time)
    attempts: int = 1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "key": self.key,
            "error": self.error,
            "timestamp": self.timestamp,
            "attempts": self.attempts,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DLQItem":
        return cls(
            key=data["key"],
            error=data["error"],
            timestamp=data.get("timestamp", time.time()),
            attempts=data.get("attempts", 1),
        )


class EvalDLQManager:
    """
    Manages checkpointing and DLQ persistence for batch evaluation tasks.
    """

    def __init__(
        self,
        checkpoint_path: Optional[Path] = None,
        dlq_path: Optional[Path] = None,
    ):
        self.checkpoint_path = Path(checkpoint_path) if checkpoint_path else None
        self.dlq_path = Path(dlq_path) if dlq_path else None

    # ── Checkpoint I/O ────────────────────────────────────────────────

    def load_checkpoint(self) -> Dict[str, TaskResult]:
        """Load completed task results from checkpoint file."""
        if not self.checkpoint_path or not self.checkpoint_path.exists():
            return {}

        try:
            with open(self.checkpoint_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            checkpoint: Dict[str, TaskResult] = {}
            for item in data.get("results", []):
                res = TaskResult(
                    index=item.get("index", 0),
                    key=item["key"],
                    value=item.get("value"),
                    error=item.get("error", ""),
                    elapsed_s=item.get("elapsed_s", 0.0),
                )
                checkpoint[res.key] = res
            logger.info(f"[DLQ] Loaded {len(checkpoint)} tasks from checkpoint {self.checkpoint_path}")
            return checkpoint
        except Exception as exc:
            logger.warning(f"[DLQ] Failed to load checkpoint {self.checkpoint_path}: {exc}")
            return {}

    def save_checkpoint(self, results: Sequence[TaskResult]) -> None:
        """Save task results to checkpoint file."""
        if not self.checkpoint_path:
            return

        try:
            self.checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
            payload = {
                "saved_at": time.time(),
                "n_results": len(results),
                "results": [
                    {
                        "index": r.index,
                        "key": r.key,
                        "value": r.value,
                        "error": r.error,
                        "elapsed_s": r.elapsed_s,
                    }
                    for r in results
                ],
            }
            with open(self.checkpoint_path, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
            logger.info(f"[DLQ] Checkpoint saved: {len(results)} items -> {self.checkpoint_path}")
        except Exception as exc:
            logger.error(f"[DLQ] Failed to save checkpoint to {self.checkpoint_path}: {exc}")

    # ── DLQ I/O ───────────────────────────────────────────────────────

    def load_dlq(self) -> Dict[str, DLQItem]:
        """Load failed tasks from DLQ file."""
        if not self.dlq_path or not self.dlq_path.exists():
            return {}

        try:
            with open(self.dlq_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            items = {d["key"]: DLQItem.from_dict(d) for d in data.get("dlq_items", [])}
            logger.info(f"[DLQ] Loaded {len(items)} failed items from DLQ {self.dlq_path}")
            return items
        except Exception as exc:
            logger.warning(f"[DLQ] Failed to load DLQ {self.dlq_path}: {exc}")
            return {}

    def save_dlq(self, dlq_items: Sequence[DLQItem]) -> None:
        """Save DLQ items to DLQ file."""
        if not self.dlq_path:
            return

        try:
            self.dlq_path.parent.mkdir(parents=True, exist_ok=True)
            payload = {
                "updated_at": time.time(),
                "n_failed": len(dlq_items),
                "dlq_items": [item.to_dict() for item in dlq_items],
            }
            with open(self.dlq_path, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
            logger.info(f"[DLQ] DLQ file saved: {len(dlq_items)} failed items -> {self.dlq_path}")
        except Exception as exc:
            logger.error(f"[DLQ] Failed to save DLQ file {self.dlq_path}: {exc}")

    # ── Execution with Checkpoint & DLQ ──────────────────────────────

    async def run_with_dlq(
        self,
        tasks: Sequence[EvalTask],
        limits: Optional[RateLimits] = None,
        on_progress: Optional[Callable[[int, int], None]] = None,
    ) -> QueueReport:
        """
        Run tasks with checkpoint skipping and automatic DLQ persistence.
        """
        cached = self.load_checkpoint()
        pending_tasks: List[EvalTask] = []
        cached_results: Dict[int, TaskResult] = {}

        for i, task in enumerate(tasks):
            if task.key in cached and cached[task.key].ok:
                # Use cached successful result
                cached_res = cached[task.key]
                cached_res.index = i  # Re-index for current submission order
                cached_results[i] = cached_res
            else:
                pending_tasks.append(task)

        if not pending_tasks:
            logger.info("[DLQ] All tasks satisfied from checkpoint!")
            all_ordered = [cached_results[i] for i in range(len(tasks))]
            return QueueReport(
                n_tasks=len(tasks),
                n_ok=len(all_ordered),
                n_failed=0,
                wall_seconds=0.0,
                results=all_ordered,
            )

        logger.info(f"[DLQ] Running {len(pending_tasks)}/{len(tasks)} pending tasks ({len(cached_results)} cached)")
        report = await run_queue(pending_tasks, limits=limits, on_progress=on_progress)

        # Merge cached and new results into submission order
        new_result_by_key = {r.key: r for r in report.results}
        final_results: List[TaskResult] = []
        new_failures: List[DLQItem] = []

        existing_dlq = self.load_dlq()

        for i, task in enumerate(tasks):
            if i in cached_results:
                final_results.append(cached_results[i])
            elif task.key in new_result_by_key:
                res = new_result_by_key[task.key]
                res.index = i
                final_results.append(res)
                if not res.ok:
                    prev_attempts = existing_dlq.get(task.key).attempts if task.key in existing_dlq else 0
                    new_failures.append(
                        DLQItem(key=task.key, error=res.error, attempts=prev_attempts + 1)
                    )

        # Save merged checkpoint & updated DLQ
        self.save_checkpoint(final_results)
        self.save_dlq(new_failures)

        return QueueReport(
            n_tasks=len(tasks),
            n_ok=sum(1 for r in final_results if r.ok),
            n_failed=sum(1 for r in final_results if not r.ok),
            wall_seconds=report.wall_seconds,
            limiter=report.limiter,
            results=final_results,
        )

    async def retry_dlq(
        self,
        task_factory: Callable[[str], Optional[EvalTask]],
        limits: Optional[RateLimits] = None,
    ) -> QueueReport:
        """
        Precision retry for failed items in DLQ.
        Only re-executes tasks listed in the DLQ file.
        """
        dlq_items = self.load_dlq()
        if not dlq_items:
            logger.info("[DLQ] No failed tasks in DLQ to retry.")
            return QueueReport(n_tasks=0, n_ok=0, n_failed=0, wall_seconds=0.0)

        tasks_to_retry: List[EvalTask] = []
        for key in dlq_items.keys():
            t = task_factory(key)
            if t is not None:
                tasks_to_retry.append(t)

        logger.info(f"[DLQ] Starting precision retry for {len(tasks_to_retry)} DLQ items...")
        retry_report = await run_queue(tasks_to_retry, limits=limits)

        # Update DLQ items and Checkpoint
        checkpoint = self.load_checkpoint()
        remaining_dlq: List[DLQItem] = []

        for res in retry_report.results:
            if res.ok:
                checkpoint[res.key] = res
                logger.info(f"[DLQ] Precision retry PASSED for task {res.key}")
            else:
                item = dlq_items.get(res.key)
                attempts = (item.attempts + 1) if item else 1
                remaining_dlq.append(DLQItem(key=res.key, error=res.error, attempts=attempts))
                logger.warning(f"[DLQ] Precision retry FAILED for task {res.key}: {res.error}")

        # Update checkpoint and DLQ files
        self.save_checkpoint(list(checkpoint.values()))
        self.save_dlq(remaining_dlq)

        return retry_report
