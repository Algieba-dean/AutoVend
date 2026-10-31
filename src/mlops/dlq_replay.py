"""
Dead Letter Queue (DLQ) & Precision Replay Engine for Failed LLM/Eval Tasks (src/mlops/dlq_replay.py).

Features:
1. Automated Failure Capture: Captures failed LLM calls, batch evaluations, and extractor tasks.
2. Exponential Backoff & Jitter: Computes adaptive retry intervals.
3. Precision Replay Scheduler: Re-executes only failed tasks with custom executor handlers.
4. Resolution Tracking: Records resolved vs dead-letter tasks, updating production checkpoints.
"""

import json
import random
import threading
import time
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from src.utils.config import PROJECT_ROOT
from src.utils.logger import get_logger

logger = get_logger(__name__)

DEFAULT_DLQ_STORAGE = PROJECT_ROOT / "storage" / "mlops" / "dlq"


class DLQTaskStatus(str, Enum):
    PENDING = "pending"
    REPLAYING = "replaying"
    RESOLVED = "resolved"
    DEAD_LETTER = "dead_letter"


@dataclass
class DLQTaskRecord:
    """A failed task captured in the Dead Letter Queue."""

    task_id: str
    task_type: str  # "llm_generation", "eval_judge", "extractor", "retrieval"
    payload: Dict[str, Any]
    error_message: str
    error_category: str = "unknown"
    attempts: int = 1
    max_attempts: int = 3
    next_retry_at: float = field(default_factory=time.time)
    status: DLQTaskStatus = DLQTaskStatus.PENDING
    created_at: float = field(default_factory=time.time)
    resolved_at: Optional[float] = None
    execution_result: Optional[Any] = None

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["status"] = self.status.value
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DLQTaskRecord":
        cp = dict(data)
        if isinstance(cp.get("status"), str):
            cp["status"] = DLQTaskStatus(cp["status"])
        return cls(**cp)


@dataclass
class DLQReplaySummary:
    """Summary of a DLQ batch replay run."""

    total_attempted: int = 0
    resolved_count: int = 0
    failed_again_count: int = 0
    dead_letter_count: int = 0
    duration_s: float = 0.0


class DLQReplayEngine:
    """
    Persistent DLQ & Retry Manager for failed LLM and evaluation operations.
    """

    def __init__(
        self,
        storage_dir: Optional[Path] = None,
        base_backoff_s: float = 1.0,
        max_backoff_s: float = 60.0,
    ):
        self.storage_dir = Path(storage_dir) if storage_dir else DEFAULT_DLQ_STORAGE
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.tasks_file = self.storage_dir / "dlq_tasks.json"
        self.base_backoff_s = base_backoff_s
        self.max_backoff_s = max_backoff_s
        self._lock = threading.RLock()
        self._tasks: Dict[str, DLQTaskRecord] = {}
        self._load_tasks()

    def _compute_next_retry(self, attempts: int) -> float:
        """Exponential backoff with full jitter: backoff = min(max_backoff, base * 2^(attempts-1)) * uniform(0.8, 1.2)."""
        backoff = min(self.max_backoff_s, self.base_backoff_s * (2 ** max(0, attempts - 1)))
        jitter = random.uniform(0.8, 1.2)
        return time.time() + (backoff * jitter)

    def enqueue_failed_task(
        self,
        task_type: str,
        payload: Dict[str, Any],
        error_message: str,
        error_category: str = "unknown",
        task_id: Optional[str] = None,
        max_attempts: int = 3,
    ) -> DLQTaskRecord:
        """Capture a failed operation in the Dead Letter Queue."""
        import uuid

        tid = task_id or f"dlq_{uuid.uuid4().hex[:12]}"
        record = DLQTaskRecord(
            task_id=tid,
            task_type=task_type,
            payload=payload,
            error_message=str(error_message),
            error_category=error_category,
            attempts=1,
            max_attempts=max_attempts,
            next_retry_at=self._compute_next_retry(1),
            status=DLQTaskStatus.PENDING,
            created_at=time.time(),
        )

        with self._lock:
            self._tasks[tid] = record
            self._save_tasks()

        logger.warning(f"[DLQ] Enqueued failed task {tid} ({task_type}): {error_message}")
        return record

    def replay_single_task(
        self,
        task_id: str,
        executor_fn: Callable[[Dict[str, Any]], Any],
    ) -> bool:
        """
        Execute precision replay for one specified DLQ task.
        """
        with self._lock:
            task = self._tasks.get(task_id)
            if not task:
                raise ValueError(f"Task {task_id} not found in DLQ")

            task.status = DLQTaskStatus.REPLAYING
            self._save_tasks()

        logger.info(
            f"[DLQ Replay] Executing task {task_id} (attempt {task.attempts + 1}/{task.max_attempts})..."
        )

        try:
            result = executor_fn(task.payload)
            with self._lock:
                task.status = DLQTaskStatus.RESOLVED
                task.resolved_at = time.time()
                task.execution_result = result
                self._save_tasks()
            logger.info(f"[DLQ Replay SUCCESS] Task {task_id} resolved successfully.")
            return True
        except Exception as exc:
            with self._lock:
                task.attempts += 1
                task.error_message = str(exc)
                if task.attempts >= task.max_attempts:
                    task.status = DLQTaskStatus.DEAD_LETTER
                    logger.error(
                        f"[DLQ EXHAUSTED] Task {task_id} exceeded max attempts ({task.max_attempts}). Moved to DEAD_LETTER."
                    )
                else:
                    task.status = DLQTaskStatus.PENDING
                    task.next_retry_at = self._compute_next_retry(task.attempts)
                    logger.warning(
                        f"[DLQ RETRY FAILED] Task {task_id} failed again: {exc}. Next retry at {task.next_retry_at}"
                    )
                self._save_tasks()
            return False

    def replay_pending_tasks(
        self,
        task_type: Optional[str] = None,
        executors: Optional[Dict[str, Callable[[Dict[str, Any]], Any]]] = None,
        force: bool = False,
    ) -> DLQReplaySummary:
        """
        Batch replay all due pending tasks using matching registered executor functions.
        """
        exec_map = executors or {}
        now = time.time()
        start_t = time.time()

        with self._lock:
            eligible = [
                t
                for t in self._tasks.values()
                if t.status == DLQTaskStatus.PENDING
                and (force or t.next_retry_at <= now)
                and (task_type is None or t.task_type == task_type)
            ]

        summary = DLQReplaySummary(total_attempted=len(eligible))

        for task in eligible:
            fn = exec_map.get(task.task_type)
            if not fn:
                logger.warning(
                    f"[DLQ] No executor registered for task_type '{task.task_type}', skipping task {task.task_id}"
                )
                continue

            success = self.replay_single_task(task.task_id, fn)
            if success:
                summary.resolved_count += 1
            else:
                summary.failed_again_count += 1
                if task.status == DLQTaskStatus.DEAD_LETTER:
                    summary.dead_letter_count += 1

        summary.duration_s = round(time.time() - start_t, 3)
        logger.info(
            f"[DLQ Batch Replay Finished] Attempted: {summary.total_attempted}, "
            f"Resolved: {summary.resolved_count}, Failed: {summary.failed_again_count} in {summary.duration_s}s"
        )
        return summary

    def list_tasks(self, status: Optional[DLQTaskStatus] = None) -> List[DLQTaskRecord]:
        """List tasks, optionally filtered by status."""
        with self._lock:
            tasks = list(self._tasks.values())
            if status is not None:
                tasks = [t for t in tasks if t.status == status]
            return sorted(tasks, key=lambda t: t.created_at, reverse=True)

    def purge_resolved(self) -> int:
        """Remove resolved tasks from storage to keep DLQ lean."""
        with self._lock:
            resolved_keys = [
                k for k, v in self._tasks.items() if v.status == DLQTaskStatus.RESOLVED
            ]
            for k in resolved_keys:
                del self._tasks[k]
            self._save_tasks()
            return len(resolved_keys)

    def _load_tasks(self) -> None:
        if not self.tasks_file.exists():
            return
        try:
            with open(self.tasks_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    for item in data:
                        rec = DLQTaskRecord.from_dict(item)
                        self._tasks[rec.task_id] = rec
        except Exception as exc:
            logger.error(f"Failed to load DLQ file {self.tasks_file}: {exc}")

    def _save_tasks(self) -> None:
        try:
            tmp_file = self.storage_dir / f"dlq_tasks_{int(time.time() * 1000)}.tmp"
            with open(tmp_file, "w", encoding="utf-8") as f:
                json.dump(
                    [t.to_dict() for t in self._tasks.values()], f, ensure_ascii=False, indent=2
                )
            tmp_file.replace(self.tasks_file)
        except OSError as exc:
            logger.warning(f"Atomic write to DLQ file failed, attempting direct write: {exc}")
            try:
                with open(self.tasks_file, "w", encoding="utf-8") as f:
                    json.dump(
                        [t.to_dict() for t in self._tasks.values()], f, ensure_ascii=False, indent=2
                    )
            except OSError:
                pass


# Global Singleton
dlq_replay_engine = DLQReplayEngine()
