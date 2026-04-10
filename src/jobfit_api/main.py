"""FastAPI application entrypoint."""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .auth import TokenVerifier, build_token_verifier
from .database import DatabaseManager
from .observability import configure_logging, install_request_logging
from .queue import check_redis_health, configure_broker
from .routes.auth import router as auth_router
from .routes.health import router as health_router
from .routes.jobs import router as jobs_router
from .routes.letters import router as letters_router
from .routes.profile import router as profile_router
from .routes.tasks import router as tasks_router
from .settings import ApiSettings
from .task_processing import EvaluatorFactory, default_evaluator_factory


def create_app(
    settings: ApiSettings | None = None,
    *,
    token_verifier: TokenVerifier | None = None,
    database_manager: DatabaseManager | None = None,
    evaluator_factory: EvaluatorFactory | None = None,
) -> FastAPI:
    settings = settings or ApiSettings.from_env()
    validation_errors = settings.validate()
    if validation_errors:
        raise RuntimeError("Invalid API configuration: " + " ".join(validation_errors))

    configure_logging(settings.log_level)
    database_manager = database_manager or DatabaseManager(settings)
    token_verifier = token_verifier or build_token_verifier(settings)
    broker = configure_broker(settings)

    app = FastAPI(
        title=settings.api_title,
        version=settings.api_version,
    )
    install_request_logging(app)
    if settings.cors_allowed_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_allowed_origins,
            allow_origin_regex=settings.cors_allowed_origin_regex,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    app.state.settings = settings
    app.state.database = database_manager
    app.state.token_verifier = token_verifier
    app.state.broker = broker
    app.state.redis_healthcheck = check_redis_health
    app.state.evaluator_factory = evaluator_factory or default_evaluator_factory

    @app.get("/", tags=["meta"])
    def get_root() -> dict[str, Any]:
        return {
            "service": settings.api_title,
            "version": settings.api_version,
            "environment": settings.app_env,
            "docs_url": "/docs",
        }

    app.include_router(health_router, prefix=settings.api_prefix)
    app.include_router(auth_router, prefix=settings.api_prefix)
    app.include_router(profile_router, prefix=settings.api_prefix)
    app.include_router(jobs_router, prefix=settings.api_prefix)
    app.include_router(letters_router, prefix=settings.api_prefix)
    app.include_router(tasks_router, prefix=settings.api_prefix)
    return app


app = create_app()


def run() -> None:
    try:
        import uvicorn
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("uvicorn is not installed.") from exc

    settings = ApiSettings.from_env()
    uvicorn.run(
        "jobfit_api.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.is_development,
    )
