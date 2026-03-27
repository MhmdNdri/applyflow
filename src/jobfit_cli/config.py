"""Configuration loading."""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path

from .constants import DEFAULT_OPENAI_MODEL


class ConfigurationError(RuntimeError):
    """Raised when required local configuration is missing."""


@dataclass(slots=True)
class AppPaths:
    root: Path
    data_dir: Path
    google_dir: Path
    profile_dir: Path
    jobs_dir: Path
    letters_dir: Path
    runs_dir: Path
    env_file: Path


@dataclass(slots=True)
class AppConfig:
    paths: AppPaths
    openai_api_key: str | None
    openai_model: str
    google_sheet_id: str | None
    google_service_account_file: Path | None
    google_oauth_client_file: Path | None
    google_oauth_token_file: Path
    google_drive_folder_id: str | None

    @classmethod
    def from_env(cls, root: Path | None = None) -> "AppConfig":
        resolved_root = (root or Path.cwd()).resolve()
        load_dotenv_file(resolved_root)

        paths = AppPaths(
            root=resolved_root,
            data_dir=resolved_root / "data",
            google_dir=resolved_root / "data" / "google",
            profile_dir=resolved_root / "data" / "profile",
            jobs_dir=resolved_root / "data" / "jobs",
            letters_dir=resolved_root / "data" / "letters",
            runs_dir=resolved_root / "data" / "runs",
            env_file=resolved_root / ".env",
        )

        service_account_value = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE")
        oauth_client_value = os.getenv("GOOGLE_OAUTH_CLIENT_FILE")
        oauth_token_value = os.getenv("GOOGLE_OAUTH_TOKEN_FILE")
        credentials_path = resolve_optional_path(resolved_root, service_account_value)
        oauth_client_path = resolve_optional_path(resolved_root, oauth_client_value)
        oauth_token_path = resolve_optional_path(
            resolved_root,
            oauth_token_value,
        ) or (paths.google_dir / "oauth-token.json")

        return cls(
            paths=paths,
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            openai_model=os.getenv("OPENAI_MODEL", DEFAULT_OPENAI_MODEL),
            google_sheet_id=os.getenv("GOOGLE_SHEET_ID"),
            google_service_account_file=credentials_path,
            google_oauth_client_file=oauth_client_path,
            google_oauth_token_file=oauth_token_path,
            google_drive_folder_id=os.getenv("GOOGLE_DRIVE_FOLDER_ID"),
        )

    def missing_openai_vars(self) -> list[str]:
        missing: list[str] = []
        if not self.openai_api_key:
            missing.append("OPENAI_API_KEY")
        return missing

    def missing_google_vars(self) -> list[str]:
        missing: list[str] = []
        if not self.google_sheet_id:
            missing.append("GOOGLE_SHEET_ID")
        if not self.google_oauth_client_file and not self.google_service_account_file:
            missing.append("GOOGLE_OAUTH_CLIENT_FILE or GOOGLE_SERVICE_ACCOUNT_FILE")
        return missing

    def google_auth_mode_label(self) -> str:
        if self.google_oauth_client_file:
            return "OAuth user credentials"
        if self.google_service_account_file:
            return "service account credentials"
        return "not configured"


def load_dotenv_file(root: Path) -> None:
    env_file = root / ".env"
    if not env_file.exists():
        return

    try:
        from dotenv import load_dotenv
    except ImportError:
        return

    load_dotenv(env_file, override=False)


def resolve_optional_path(root: Path, value: str | None) -> Path | None:
    if not value:
        return None

    candidate = Path(value).expanduser()
    if not candidate.is_absolute():
        candidate = (root / candidate).resolve()

    return candidate
