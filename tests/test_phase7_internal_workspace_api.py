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
from jobfit_core.models import JobEvaluation
from jobfit_core.prompts import ApplicantProfile


class FakeTokenVerifier(TokenVerifier):
    def verify_token(self, token: str) -> AuthContext:
        if token != "valid-token":
            raise AuthenticationError("Token is invalid.")
        return AuthContext(
            user_id="clerk_user_123",
            session_id="sess_123",
            email="person@example.com",
            raw_claims={"sub": "clerk_user_123"},
        )


class FakeEvaluator:
    def __init__(self) -> None:
        self.active_model = "gpt-5.4-mini"

    def evaluate(self, resume_text: str, context_text: str, job_description: str) -> JobEvaluation:
        return JobEvaluation.model_validate(
            {
                "score": 82,
                "verdict": "strong_fit",
                "company": "Lendable",
                "role_title": "Senior React Engineer",
                "location": "London, UK",
                "source_url": None,
                "top_strengths": ["React", "TypeScript", "Delivery"],
                "critical_gaps": ["Accessibility", "Observability", "Scale"],
                "feedback": "Strong fit with a few visible gaps.",
            }
        )

    def generate_cover_letter(
        self,
        resume_text: str,
        context_text: str,
        job_description: str,
        evaluation: JobEvaluation,
        applicant_profile: ApplicantProfile,
        cover_letter_date: str,
    ) -> str:
        return (
            f"{cover_letter_date}\n\n"
            "Dear Hiring Team,\n\n"
            "Paragraph one.\n\n"
            "Paragraph two.\n\n"
            "Paragraph three.\n\n"
            "Best regards,\n"
            f"{applicant_profile.full_name or 'Mohammad Naderi'}"
        )


class PhaseSevenInternalWorkspaceApiTests(unittest.TestCase):
    def test_cover_letters_route_lists_internal_letters(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            settings = self._build_settings(root)
            database = DatabaseManager(settings)
            database.create_all()
            app = create_app(
                settings,
                token_verifier=FakeTokenVerifier(),
                database_manager=database,
                evaluator_factory=lambda _root: FakeEvaluator(),
            )

            with TestClient(app) as client:
                client.post(
                    "/api/v1/profile",
                    headers=self._auth_headers(),
                    json={
                        "display_name": "Mohammad Naderi",
                        "location": "London",
                        "resume_text": "Mohammad Naderi\nResume with React and TypeScript experience.",
                        "context_text": "Honest context",
                    },
                )
                job_id = client.post(
                    "/api/v1/jobs",
                    headers=self._auth_headers(),
                    json={
                        "company": "Lendable",
                        "role_title": "Senior React Engineer",
                        "description": "Detailed React job description.",
                        "current_status": "applied",
                    },
                ).json()["id"]

                task_id = client.post(
                    f"/api/v1/jobs/{job_id}/score",
                    headers=self._auth_headers(),
                ).json()["task_id"]
                client.get(f"/api/v1/tasks/{task_id}", headers=self._auth_headers())

                letters_response = client.get("/api/v1/cover-letters", headers=self._auth_headers())
                self.assertEqual(letters_response.status_code, 200)
                payload = letters_response.json()
                self.assertEqual(len(payload), 1)
                self.assertEqual(payload[0]["job_id"], job_id)
                self.assertEqual(payload[0]["company"], "Lendable")
                self.assertEqual(payload[0]["role_title"], "Senior React Engineer")
                self.assertEqual(payload[0]["current_status"], "applied")
                self.assertEqual(payload[0]["score"], 82)
                self.assertIn("Best regards", payload[0]["content"])

                jobs_payload = client.get("/api/v1/jobs", headers=self._auth_headers()).json()
                self.assertIsNotNone(jobs_payload[0]["latest_cover_letter"])
                self.assertEqual(jobs_payload[0]["latest_cover_letter"]["id"], payload[0]["id"])

                integration_response = client.get("/api/v1/integrations/google", headers=self._auth_headers())
                self.assertEqual(integration_response.status_code, 404)
            database.dispose()

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

    def _auth_headers(self) -> dict[str, str]:
        return {"Authorization": "Bearer valid-token"}
