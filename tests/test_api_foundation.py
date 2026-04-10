from __future__ import annotations

import os
import sys
from pathlib import Path
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["AUTH_ENABLED"] = "false"
os.environ["REDIS_URL"] = ""

from fastapi.testclient import TestClient

from jobfit_api.auth import AuthContext, AuthenticationError, TokenVerifier
from jobfit_api.database import DatabaseManager
from jobfit_api.main import create_app
from jobfit_api.settings import ApiSettings


class FakeTokenVerifier(TokenVerifier):
    def verify_token(self, token: str) -> AuthContext:
        if token != "valid-token":
            raise AuthenticationError("Token is invalid.")
        return AuthContext(
            user_id="user_123",
            session_id="sess_123",
            email="person@example.com",
            raw_claims={"sub": "user_123"},
        )


class ApiFoundationTests(unittest.TestCase):
    def test_health_endpoint_reports_database_ok(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            settings = self._build_settings(root)
            database = DatabaseManager(settings)
            database.create_all()
            app = create_app(settings, token_verifier=FakeTokenVerifier(), database_manager=database)

            with TestClient(app) as client:
                response = client.get("/api/v1/health")
            database.dispose()

            self.assertEqual(response.status_code, 200)
            payload = response.json()
            self.assertEqual(payload["status"], "ok")
            self.assertEqual(payload["services"]["database"]["status"], "ok")
            self.assertEqual(payload["services"]["redis"]["status"], "not_configured")
            self.assertTrue(response.headers.get("x-request-id"))

    def test_auth_me_endpoint_returns_verified_subject(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            settings = self._build_settings(root)
            database = DatabaseManager(settings)
            database.create_all()
            app = create_app(settings, token_verifier=FakeTokenVerifier(), database_manager=database)

            with TestClient(app) as client:
                response = client.get(
                    "/api/v1/auth/me",
                    headers={"Authorization": "Bearer valid-token"},
                )
            database.dispose()

            self.assertEqual(response.status_code, 200)
            self.assertEqual(
                response.json(),
                {
                    "user_id": "user_123",
                    "session_id": "sess_123",
                    "email": "person@example.com",
                },
            )

    def test_auth_me_endpoint_rejects_missing_token(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            settings = self._build_settings(root)
            database = DatabaseManager(settings)
            database.create_all()
            app = create_app(settings, token_verifier=FakeTokenVerifier(), database_manager=database)

            with TestClient(app) as client:
                response = client.get("/api/v1/auth/me")
            database.dispose()

            self.assertEqual(response.status_code, 401)
            self.assertEqual(response.json()["detail"], "Missing bearer token.")

    def test_create_app_rejects_missing_clerk_config_when_auth_is_enabled(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            settings = ApiSettings(
                root=root,
                app_env="test",
                api_host="127.0.0.1",
                api_port=8000,
                api_prefix="/api/v1",
                api_title="Applyflow API",
                api_version="0.1.0",
                database_url=f"sqlite:///{(root / 'test.db').resolve()}",
                database_echo=False,
                redis_url=None,
                auth_enabled=True,
                clerk_issuer=None,
                clerk_jwks_url=None,
                clerk_audience=None,
                clerk_authorized_party=None,
            )

            with self.assertRaises(RuntimeError) as raised:
                create_app(settings)

            self.assertIn("CLERK_ISSUER", str(raised.exception))
            self.assertIn("CLERK_JWKS_URL", str(raised.exception))

    def _build_settings(self, root: Path) -> ApiSettings:
        return ApiSettings(
            root=root,
            app_env="test",
            api_host="127.0.0.1",
            api_port=8000,
            api_prefix="/api/v1",
            api_title="Applyflow API",
            api_version="0.1.0",
            database_url=f"sqlite:///{(root / 'test.db').resolve()}",
            database_echo=False,
            redis_url=None,
            auth_enabled=True,
            clerk_issuer="https://example.clerk.accounts.dev",
            clerk_jwks_url="https://example.clerk.accounts.dev/.well-known/jwks.json",
            clerk_audience=None,
            clerk_authorized_party=None,
        )


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
