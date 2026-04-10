"""API settings and environment loading."""

from __future__ import annotations

from dataclasses import dataclass, field
import os
from pathlib import Path

from jobfit_cli.config import load_dotenv_file


def parse_bool(value: str | None, *, default: bool) -> bool:
    if value is None:
        return default
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    return default


def normalize_database_url(value: str) -> str:
    if value.startswith("postgresql+"):
        return value
    if value.startswith("postgresql://"):
        return value.replace("postgresql://", "postgresql+psycopg://", 1)
    if value.startswith("postgres://"):
        return value.replace("postgres://", "postgresql+psycopg://", 1)
    return value


def parse_csv(value: str | None) -> list[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


@dataclass(slots=True)
class ApiSettings:
    root: Path
    app_env: str
    api_host: str
    api_port: int
    api_prefix: str
    api_title: str
    api_version: str
    database_url: str
    database_echo: bool
    redis_url: str | None
    auth_enabled: bool
    clerk_issuer: str | None
    clerk_jwks_url: str | None
    clerk_audience: str | None
    clerk_authorized_party: str | None
    frontend_base_url: str = "http://127.0.0.1:5173"
    log_level: str = "INFO"
    cors_allowed_origins: list[str] = field(default_factory=list)
    cors_allowed_origin_regex: str | None = None

    @classmethod
    def from_env(cls, root: Path | None = None) -> "ApiSettings":
        resolved_root = (root or Path.cwd()).resolve()
        load_dotenv_file(resolved_root)

        data_dir = resolved_root / "data"
        data_dir.mkdir(parents=True, exist_ok=True)

        app_env = os.getenv("APP_ENV", "development")
        api_prefix = os.getenv("API_PREFIX", "/api/v1")
        api_port = int(os.getenv("API_PORT", "8000"))
        default_database_url = f"sqlite:///{(data_dir / 'applyflow-dev.db').resolve().as_posix()}"
        return cls(
            root=resolved_root,
            app_env=app_env,
            api_host=os.getenv("API_HOST", "0.0.0.0"),
            api_port=api_port,
            api_prefix=api_prefix,
            api_title=os.getenv("API_TITLE", "Applyflow API"),
            api_version=os.getenv("API_VERSION", "0.1.0"),
            database_url=normalize_database_url(os.getenv("DATABASE_URL", default_database_url)),
            database_echo=parse_bool(os.getenv("DATABASE_ECHO"), default=False),
            redis_url=os.getenv("REDIS_URL"),
            auth_enabled=parse_bool(os.getenv("AUTH_ENABLED"), default=True),
            clerk_issuer=os.getenv("CLERK_ISSUER"),
            clerk_jwks_url=os.getenv("CLERK_JWKS_URL"),
            clerk_audience=os.getenv("CLERK_AUDIENCE"),
            clerk_authorized_party=os.getenv("CLERK_AUTHORIZED_PARTY"),
            frontend_base_url=os.getenv("FRONTEND_BASE_URL", "http://127.0.0.1:5173").rstrip("/"),
            log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
            cors_allowed_origins=parse_csv(
                os.getenv(
                    "CORS_ALLOWED_ORIGINS",
                    "http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000,http://127.0.0.1:3000",
                )
            ),
            cors_allowed_origin_regex=os.getenv(
                "CORS_ALLOWED_ORIGIN_REGEX",
                r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$",
            ),
        )

    @property
    def is_development(self) -> bool:
        return self.app_env == "development"

    def validate(self) -> list[str]:
        errors: list[str] = []
        if self.auth_enabled:
            if not self.clerk_issuer:
                errors.append("CLERK_ISSUER must be configured when AUTH_ENABLED=true.")
            if not self.clerk_jwks_url:
                errors.append("CLERK_JWKS_URL must be configured when AUTH_ENABLED=true.")
        elif self.app_env == "production":
            errors.append("AUTH_ENABLED cannot be false in production.")

        if self.app_env == "production" and self.database_url.startswith("sqlite"):
            errors.append("SQLite is not supported for production API deployments.")

        return errors
