"""Dramatiq worker entrypoint for background tasks."""

from __future__ import annotations

import os

from .queue import configure_broker
from .settings import ApiSettings

settings = ApiSettings.from_env()
configure_broker(settings)

import dramatiq


@dramatiq.actor(queue_name="jobfit_tasks", max_retries=0)
def run_task_actor(task_id: str) -> None:
    from .task_processing import default_evaluator_factory, run_task

    current_settings = ApiSettings.from_env()
    run_task(current_settings, default_evaluator_factory, task_id)


def run() -> None:
    os.execvp("dramatiq", ["dramatiq", "jobfit_api.worker"])


if __name__ == "__main__":  # pragma: no cover
    run()
