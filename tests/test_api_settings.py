from __future__ import annotations

import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from jobfit_api.settings import ApiSettings, normalize_database_url, parse_csv


class ApiSettingsTests(unittest.TestCase):
    def test_parse_csv_ignores_blank_segments(self) -> None:
        self.assertEqual(parse_csv("http://a.test, ,http://b.test"), ["http://a.test", "http://b.test"])

    def test_normalize_database_url_upgrades_plain_postgresql_url(self) -> None:
        self.assertEqual(
            normalize_database_url("postgresql://user:pass@host/db"),
            "postgresql+psycopg://user:pass@host/db",
        )

    def test_normalize_database_url_upgrades_legacy_postgres_url(self) -> None:
        self.assertEqual(
            normalize_database_url("postgres://user:pass@host/db"),
            "postgresql+psycopg://user:pass@host/db",
        )

    def test_from_env_normalizes_database_url(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with patch.dict(
                os.environ,
                {
                    "DATABASE_URL": "postgresql://user:pass@host/db",
                },
                clear=True,
            ):
                settings = ApiSettings.from_env(root)

        self.assertEqual(settings.database_url, "postgresql+psycopg://user:pass@host/db")

    def test_from_env_reads_cors_allowed_origins(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with patch.dict(
                os.environ,
                {
                    "CORS_ALLOWED_ORIGINS": "http://localhost:5173,http://127.0.0.1:5173",
                },
                clear=True,
            ):
                settings = ApiSettings.from_env(root)

        self.assertEqual(
            settings.cors_allowed_origins,
            ["http://localhost:5173", "http://127.0.0.1:5173"],
        )
        self.assertEqual(settings.cors_allowed_origin_regex, r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$")

    def test_validate_requires_clerk_settings_when_auth_is_enabled(self) -> None:
        settings = ApiSettings(
            root=Path.cwd(),
            app_env="test",
            api_host="127.0.0.1",
            api_port=8000,
            api_prefix="/api/v1",
            api_title="Applyflow API",
            api_version="0.1.0",
            database_url="sqlite:///:memory:",
            database_echo=False,
            redis_url=None,
            auth_enabled=True,
            clerk_issuer=None,
            clerk_jwks_url=None,
            clerk_audience=None,
            clerk_authorized_party=None,
        )

        errors = settings.validate()
        self.assertEqual(len(errors), 2)
        self.assertIn("CLERK_ISSUER", errors[0])
        self.assertIn("CLERK_JWKS_URL", errors[1])


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
