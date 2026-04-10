"""Redis and Dramatiq foundation wiring."""

from __future__ import annotations

from typing import Any

from fastapi import BackgroundTasks, FastAPI


def dispatch_task(app: FastAPI, background_tasks: BackgroundTasks, task_id: str) -> str:
    settings = app.state.settings

    if settings.redis_url:
        from .worker import run_task_actor

        run_task_actor.send(task_id)
        return "worker"

    from .task_processing import run_task

    background_tasks.add_task(run_task, settings, app.state.evaluator_factory, task_id)
    return "in_process"


def schedule_task_retry(settings, task_id: str, *, delay_ms: int) -> str:
    if not settings.redis_url:
        raise RuntimeError("Cannot schedule a delayed retry without REDIS_URL configured.")

    from .worker import run_task_actor

    run_task_actor.send_with_options(args=(task_id,), delay=delay_ms)
    return "worker_delayed"


def configure_broker(settings) -> Any:
    try:
        import dramatiq
        from dramatiq.brokers.redis import RedisBroker
        from dramatiq.brokers.stub import StubBroker
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("Dramatiq is not installed.") from exc

    broker = RedisBroker(url=settings.redis_url) if settings.redis_url else StubBroker()
    dramatiq.set_broker(broker)
    return broker


def check_redis_health(settings) -> tuple[str, str]:
    if not settings.redis_url:
        return "not_configured", "REDIS_URL is not configured."

    try:
        import redis
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("redis is not installed.") from exc

    client = redis.from_url(settings.redis_url)
    client.ping()
    return "ok", "Redis ping succeeded."
