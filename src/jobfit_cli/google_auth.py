"""Shared Google authentication helpers."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

from .config import ConfigurationError


@dataclass(slots=True)
class GoogleAuthSettings:
    service_account_file: Path | None
    oauth_client_file: Path | None
    oauth_token_file: Path | None

    @property
    def prefers_oauth(self) -> bool:
        return self.oauth_client_file is not None

    @property
    def mode_label(self) -> str:
        if self.prefers_oauth:
            return "OAuth user credentials"
        if self.service_account_file:
            return "service account credentials"
        return "not configured"


def load_google_dependencies(
    *,
    auth_settings: GoogleAuthSettings,
    scopes: list[str],
) -> tuple[Any, Any]:
    credentials = load_google_credentials(auth_settings=auth_settings, scopes=scopes)

    try:
        from googleapiclient.discovery import build
    except ImportError as exc:  # pragma: no cover - depends on local environment
        raise ConfigurationError(
            "Google API packages are not installed. Run `pip install -e .` first."
        ) from exc

    return credentials, build


def load_google_credentials(
    *,
    auth_settings: GoogleAuthSettings,
    scopes: list[str],
) -> Any:
    if auth_settings.prefers_oauth:
        return load_google_oauth_credentials(
            client_file=auth_settings.oauth_client_file,
            token_file=auth_settings.oauth_token_file,
            scopes=scopes,
        )
    if auth_settings.service_account_file:
        return load_google_service_account_credentials(
            service_account_file=auth_settings.service_account_file,
            scopes=scopes,
        )
    raise ConfigurationError(
        "Missing Google auth configuration. Set GOOGLE_OAUTH_CLIENT_FILE or GOOGLE_SERVICE_ACCOUNT_FILE."
    )


def load_google_service_account_credentials(
    *,
    service_account_file: Path,
    scopes: list[str],
) -> Any:
    if not service_account_file.exists():
        raise ConfigurationError(f"Google credentials file not found: {service_account_file}")

    try:
        from google.oauth2 import service_account
    except ImportError as exc:  # pragma: no cover - depends on local environment
        raise ConfigurationError(
            "Google auth packages are not installed. Run `pip install -e .` first."
        ) from exc

    return service_account.Credentials.from_service_account_file(
        str(service_account_file),
        scopes=scopes,
    )


def load_google_oauth_credentials(
    *,
    client_file: Path | None,
    token_file: Path | None,
    scopes: list[str],
) -> Any:
    if not client_file:
        raise ConfigurationError("Missing GOOGLE_OAUTH_CLIENT_FILE.")
    if not client_file.exists():
        raise ConfigurationError(f"Google OAuth client file not found: {client_file}")
    if token_file is None:
        raise ConfigurationError("Missing Google OAuth token path.")

    try:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
    except ImportError as exc:  # pragma: no cover - depends on local environment
        raise ConfigurationError(
            (
                "Google OAuth packages are not installed. "
                "Run `pip install -e .` first."
            )
        ) from exc

    credentials = None
    if token_file.exists():
        credentials = Credentials.from_authorized_user_file(str(token_file), scopes=scopes)
        if not token_has_required_scopes(credentials=credentials, scopes=scopes):
            credentials = None

    if credentials and credentials.expired and credentials.refresh_token:
        credentials.refresh(Request())

    if not credentials or not credentials.valid:
        flow = InstalledAppFlow.from_client_secrets_file(str(client_file), scopes=scopes)
        credentials = flow.run_local_server(port=0, open_browser=True)
    token_file.parent.mkdir(parents=True, exist_ok=True)
    token_file.write_text(credentials.to_json(), encoding="utf-8")

    return credentials


def token_has_required_scopes(*, credentials: Any, scopes: list[str]) -> bool:
    granted_scopes = set(credentials.scopes or [])
    if not granted_scopes:
        granted_scopes = set(json.loads(credentials.to_json()).get("scopes", []))
    return set(scopes).issubset(granted_scopes)
