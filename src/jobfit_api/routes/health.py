"""Health endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Request

from jobfit_api.schemas import HealthResponse, ServiceHealth

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def get_health(request: Request) -> HealthResponse:
    database = request.app.state.database
    settings = request.app.state.settings

    services: dict[str, ServiceHealth] = {}

    try:
        database.healthcheck()
        services["database"] = ServiceHealth(status="ok", detail="Database query succeeded.")
    except Exception as exc:  # pragma: no cover - behavior exercised via tests with fake DB manager
        services["database"] = ServiceHealth(status="degraded", detail=str(exc))

    try:
        redis_status, redis_detail = request.app.state.redis_healthcheck(settings)
        services["redis"] = ServiceHealth(status=redis_status, detail=redis_detail)
    except Exception as exc:  # pragma: no cover
        services["redis"] = ServiceHealth(status="degraded", detail=str(exc))

    overall_status = "ok" if all(service.status != "degraded" for service in services.values()) else "degraded"
    return HealthResponse(
        status=overall_status,
        environment=settings.app_env,
        services=services,
    )
