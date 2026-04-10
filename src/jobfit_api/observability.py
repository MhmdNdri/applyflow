"""Request logging and runtime observability helpers."""

from __future__ import annotations

from contextvars import ContextVar
import json
import logging
import time
from uuid import uuid4

from fastapi import FastAPI, Request

request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)


def configure_logging(log_level: str) -> None:
    root_logger = logging.getLogger()
    if not root_logger.handlers:
        logging.basicConfig(level=getattr(logging, log_level.upper(), logging.INFO))
    else:
        root_logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))


def install_request_logging(app: FastAPI) -> None:
    logger = logging.getLogger("jobfit_api.request")

    @app.middleware("http")
    async def request_logging_middleware(request: Request, call_next):
        request_id = request.headers.get("x-request-id") or uuid4().hex
        request.state.request_id = request_id
        token = request_id_var.set(request_id)
        started_at = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            elapsed_ms = round((time.perf_counter() - started_at) * 1000, 2)
            logger.exception(
                json.dumps(
                    {
                        "event": "request.failed",
                        "request_id": request_id,
                        "method": request.method,
                        "path": request.url.path,
                        "duration_ms": elapsed_ms,
                    }
                )
            )
            request_id_var.reset(token)
            raise

        elapsed_ms = round((time.perf_counter() - started_at) * 1000, 2)
        response.headers["X-Request-ID"] = request_id
        logger.info(
            json.dumps(
                {
                    "event": "request.completed",
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "duration_ms": elapsed_ms,
                }
            )
        )
        request_id_var.reset(token)
        return response

