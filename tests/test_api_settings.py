from __future__ import annotations

import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from jobfit_api.settings import (
    ApiSettings,
    merge_origins,
    normalize_database_url,
    normalize_origin,
    parse_csv,
    parse_optional_string,
)


class ApiSettingsTests(unittest.TestCase):
    def test_parse_csv_ignores_blank_segments(self) -> None:
        self.assertEqual(parse_csv("http://a.test, ,http://b.test"), ["http://a.test", "http://b.test"])

    def test_parse_optional_string_treats_blank_as_none(self) -> None:
        self.assertIsNone(parse_optional_string(""))
        self.assertIsNone(parse_optional_string("   "))
        self.assertEqual(parse_optional_string(" value "), "value")

    def test_normalize_origin_removes_trailing_slash(self) -> None:
        self.assertEqual(normalize_origin(" https://applyflow.vercel.app/ "), "https://applyflow.vercel.app")

    def test_merge_origins_deduplicates_normalized_values(self) -> None:
        self.assertEqual(
            merge_origins(["https://a.test/"], ["https://a.test", "https://b.test"]),
            ["https://a.test", "https://b.test"],
        )

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

    def test_from_env_adds_frontend_base_url_to_cors_origins(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with patch.dict(
                os.environ,
                {
                    "FRONTEND_BASE_URL": "https://applyflow.vercel.app/",
                    "CORS_ALLOWED_ORIGINS": "https://preview.vercel.app",
                },
                clear=True,
            ):
                settings = ApiSettings.from_env(root)

        self.assertEqual(
            settings.cors_allowed_origins,
            ["https://preview.vercel.app", "https://applyflow.vercel.app"],
        )

    def test_from_env_reads_task_execution_mode(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with patch.dict(
                os.environ,
                {
                    "TASK_EXECUTION_MODE": "INLINE",
                },
                clear=True,
            ):
                settings = ApiSettings.from_env(root)

        self.assertEqual(settings.task_execution_mode, "inline")

    def test_from_env_does_not_create_data_directory_when_database_url_is_configured(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with patch.dict(
                os.environ,
                {
                    "DATABASE_URL": "postgresql://user:pass@host/db",
                },
                clear=True,
            ):
                ApiSettings.from_env(root)

            self.assertFalse((root / "data").exists())

    def test_from_env_creates_data_directory_for_blank_database_url_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with patch.dict(
                os.environ,
                {
                    "DATABASE_URL": "",
                },
                clear=True,
            ):
                settings = ApiSettings.from_env(root)

            self.assertTrue((root / "data").exists())
            self.assertTrue(settings.database_url.startswith("sqlite:///"))

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

    def test_validate_rejects_unknown_task_execution_mode(self) -> None:
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
            auth_enabled=False,
            clerk_issuer=None,
            clerk_jwks_url=None,
            clerk_audience=None,
            clerk_authorized_party=None,
            task_execution_mode="magic",
        )

        errors = settings.validate()
        self.assertEqual(errors, ["TASK_EXECUTION_MODE must be either 'background' or 'inline'."])


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
