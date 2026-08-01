"""
Tests for EvalDLQManager (Checkpointing & Failures DLQ).
"""

import json
import pytest
from pathlib import Path

from src.eval.async_runner import EvalTask, QueueReport, TaskResult
from src.eval.dlq import DLQItem, EvalDLQManager


@pytest.fixture
def temp_eval_dir(tmp_path):
    return tmp_path / "eval_test"


class TestEvalDLQManager:
    def test_checkpoint_io(self, temp_eval_dir):
        ckpt_path = temp_eval_dir / "checkpoint.json"
        manager = EvalDLQManager(checkpoint_path=ckpt_path)

        results = [
            TaskResult(index=0, key="task_1", value={"score": 0.95}),
            TaskResult(index=1, key="task_2", error="Timeout", elapsed_s=1.2),
        ]

        manager.save_checkpoint(results)
        assert ckpt_path.exists()

        loaded = manager.load_checkpoint()
        assert len(loaded) == 2
        assert loaded["task_1"].ok is True
        assert loaded["task_1"].value == {"score": 0.95}
        assert loaded["task_2"].ok is False
        assert loaded["task_2"].error == "Timeout"

    def test_dlq_io(self, temp_eval_dir):
        dlq_path = temp_eval_dir / "dlq.json"
        manager = EvalDLQManager(dlq_path=dlq_path)

        dlq_items = [
            DLQItem(key="q_101", error="500 Internal Server Error", attempts=1),
            DLQItem(key="q_102", error="429 Rate Limit", attempts=2),
        ]

        manager.save_dlq(dlq_items)
        assert dlq_path.exists()

        loaded = manager.load_dlq()
        assert len(loaded) == 2
        assert loaded["q_101"].error == "500 Internal Server Error"
        assert loaded["q_102"].attempts == 2

    @pytest.mark.asyncio
    async def test_run_with_dlq_and_checkpoint_skipping(self, temp_eval_dir):
        ckpt_path = temp_eval_dir / "checkpoint.json"
        dlq_path = temp_eval_dir / "dlq.json"
        manager = EvalDLQManager(checkpoint_path=ckpt_path, dlq_path=dlq_path)

        # Task 1 succeeds, Task 2 fails
        executed = []

        def task_fn_1():
            executed.append("task_1")
            return "ok_1"

        def task_fn_2():
            executed.append("task_2")
            raise ValueError("simulated failure on task_2")

        tasks = [
            EvalTask(key="task_1", fn=task_fn_1),
            EvalTask(key="task_2", fn=task_fn_2),
        ]

        # First run
        report = await manager.run_with_dlq(tasks)
        assert report.n_tasks == 2
        assert report.n_ok == 1
        assert report.n_failed == 1
        assert executed == ["task_1", "task_2"]

        # Check DLQ file
        dlq_loaded = manager.load_dlq()
        assert "task_2" in dlq_loaded
        assert "simulated failure" in dlq_loaded["task_2"].error

        # Reset execution tracker
        executed.clear()

        # Second run: task_1 should be loaded from checkpoint and SKIPPED
        report2 = await manager.run_with_dlq(tasks)
        assert report2.n_ok == 1
        assert report2.n_failed == 1
        # task_1 was skipped (not re-executed), only task_2 ran
        assert executed == ["task_2"]

    @pytest.mark.asyncio
    async def test_precision_retry_dlq(self, temp_eval_dir):
        ckpt_path = temp_eval_dir / "checkpoint.json"
        dlq_path = temp_eval_dir / "dlq.json"
        manager = EvalDLQManager(checkpoint_path=ckpt_path, dlq_path=dlq_path)

        # Initial DLQ state with failed task_2
        manager.save_dlq([DLQItem(key="task_2", error="Network error", attempts=1)])

        # Task factory providing fixed implementation for retry
        def retry_factory(key: str):
            if key == "task_2":
                return EvalTask(key="task_2", fn=lambda: "recovered_val")
            return None

        # Execute precision retry
        retry_report = await manager.retry_dlq(retry_factory)

        assert retry_report.n_tasks == 1
        assert retry_report.n_ok == 1
        assert retry_report.results[0].value == "recovered_val"

        # DLQ should now be empty!
        dlq_remaining = manager.load_dlq()
        assert len(dlq_remaining) == 0

        # Checkpoint should contain task_2!
        ckpt = manager.load_checkpoint()
        assert "task_2" in ckpt
        assert ckpt["task_2"].ok is True
        assert ckpt["task_2"].value == "recovered_val"
