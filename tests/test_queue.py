from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from jobfit_api.queue import dispatch_task, schedule_task_retry


class FakeBackgroundTasks:
    def __init__(self) -> None:
        self.calls: list[tuple[object, tuple[object, ...]]] = []

    def add_task(self, func, *args) -> None:
        self.calls.append((func, args))


class QueueDispatchTests(unittest.TestCase):
    def test_dispatch_task_falls_back_to_in_process_when_redis_is_not_configured(self) -> None:
        settings = SimpleNamespace(redis_url=None)
        app = SimpleNamespace(
            state=SimpleNamespace(
                settings=settings,
                evaluator_factory="fake-evaluator-factory",
            )
        )
        background_tasks = FakeBackgroundTasks()

        mode = dispatch_task(app, background_tasks, "task-123")

        self.assertEqual(mode, "in_process")
        self.assertEqual(len(background_tasks.calls), 1)
        _, args = background_tasks.calls[0]
        self.assertEqual(args[0], settings)
        self.assertEqual(args[1], "fake-evaluator-factory")
        self.assertEqual(args[2], "task-123")

    def test_dispatch_task_uses_dramatiq_worker_when_redis_is_configured(self) -> None:
        app = SimpleNamespace(
            state=SimpleNamespace(
                settings=SimpleNamespace(redis_url="redis://localhost:6379/0"),
                evaluator_factory="fake-evaluator-factory",
            )
        )
        background_tasks = FakeBackgroundTasks()

        with patch("jobfit_api.worker.run_task_actor.send") as send_mock:
            mode = dispatch_task(app, background_tasks, "task-456")

        self.assertEqual(mode, "worker")
        send_mock.assert_called_once_with("task-456")
        self.assertEqual(background_tasks.calls, [])

    def test_schedule_task_retry_uses_delayed_worker_message(self) -> None:
        settings = SimpleNamespace(redis_url="redis://localhost:6379/0")

        with patch("jobfit_api.worker.run_task_actor.send_with_options") as send_with_options_mock:
            mode = schedule_task_retry(settings, "task-789", delay_ms=15_000)

        self.assertEqual(mode, "worker_delayed")
        send_with_options_mock.assert_called_once_with(args=("task-789",), delay=15_000)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
