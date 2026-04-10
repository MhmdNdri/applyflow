from __future__ import annotations

import os
import sys
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["AUTH_ENABLED"] = "false"
os.environ["REDIS_URL"] = ""

from fastapi.testclient import TestClient

from jobfit_api.auth import AuthContext, AuthenticationError, TokenVerifier
from jobfit_api.database import DatabaseManager
from jobfit_api.main import create_app
from jobfit_api.models import ApplicationStatus, BackgroundTask, BackgroundTaskStatus, BackgroundTaskType
from jobfit_api.settings import ApiSettings
from jobfit_api.task_processing import run_task
from jobfit_api.services import create_background_task, create_job_state, create_profile_state, ensure_user
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
        self.active_model = "gpt-4o-mini"

    def evaluate(
        self,
        resume_text: str,
        context_text: str,
        job_description: str,
    ) -> JobEvaluation:
        assert "Resume" in resume_text
        assert context_text
        assert job_description
        return JobEvaluation.model_validate(
            {
                "score": 86,
                "verdict": "strong_fit",
                "company": "Lendable",
                "role_title": "Senior React Engineer",
                "location": "London, UK",
                "source_url": None,
                "top_strengths": ["React", "TypeScript", "Product delivery"],
                "critical_gaps": ["Accessibility", "Observability", "Fintech scale"],
                "feedback": "Strong fit overall. Good frontend alignment. A few gaps remain.",
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
        assert applicant_profile.full_name == "Mohammad Naderi"
        assert evaluation.score == 86
        return (
            f"{cover_letter_date}\n\n"
            "Dear Hiring Team,\n\n"
            "Paragraph one.\n\n"
            "Paragraph two.\n\n"
            "Paragraph three.\n\n"
            "Best regards,\n"
            "Mohammad Naderi"
        )


class FallbackProfileEvaluator(FakeEvaluator):
    def generate_cover_letter(
        self,
        resume_text: str,
        context_text: str,
        job_description: str,
        evaluation: JobEvaluation,
        applicant_profile: ApplicantProfile,
        cover_letter_date: str,
    ) -> str:
        assert applicant_profile.full_name == "Profile Name"
        assert applicant_profile.email == "person@example.com"
        assert applicant_profile.phone is None
        return (
            f"{cover_letter_date}\n\n"
            "Dear Hiring Team,\n\n"
            "Paragraph one.\n\n"
            "Paragraph two.\n\n"
            "Paragraph three.\n\n"
            "Best regards,\n"
            "Profile Name"
        )


class PhaseFourApiTests(unittest.TestCase):
    def test_score_task_persists_evaluation_and_cover_letter(self) -> None:
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
                        "resume_text": (
                            "Mohammad Naderi\n"
                            "m.n.mohammad.naderi@gmail.com\n"
                            "+44 7700 900123\n"
                            "Resume with React and TypeScript experience."
                        ),
                        "context_text": "Honest context",
                    },
                )

                job_response = client.post(
                    "/api/v1/jobs",
                    headers=self._auth_headers(),
                    json={
                        "company": "Lendable",
                        "role_title": "Senior React Engineer",
                        "description": "Detailed React job description.",
                    },
                )
                job_id = job_response.json()["id"]

                response = client.post(
                    f"/api/v1/jobs/{job_id}/score",
                    headers=self._auth_headers(),
                )
                self.assertEqual(response.status_code, 202)
                task_id = response.json()["task_id"]

                task_response = client.get(
                    f"/api/v1/tasks/{task_id}",
                    headers=self._auth_headers(),
                )
                self.assertEqual(task_response.status_code, 200)
                task_payload = task_response.json()
                self.assertEqual(task_payload["status"], "completed")
                self.assertEqual(task_payload["task_type"], "score_job")
                self.assertEqual(task_payload["result"]["score"], 86)
                self.assertIn("evaluation_id", task_payload["result"])
                self.assertIn("cover_letter_id", task_payload["result"])

                job_detail = client.get(
                    f"/api/v1/jobs/{job_id}",
                    headers=self._auth_headers(),
                ).json()
                self.assertIsNotNone(job_detail["latest_evaluation"])
                self.assertIsNotNone(job_detail["latest_cover_letter"])
                self.assertIsNotNone(job_detail["latest_task"])
                self.assertEqual(job_detail["latest_evaluation"]["score"], 86)
                self.assertEqual(job_detail["latest_task"]["status"], "completed")
                self.assertEqual(job_detail["latest_cover_letter"]["evaluation_id"], job_detail["latest_evaluation"]["id"])
                self.assertIn("Best regards,\nMohammad Naderi", job_detail["latest_cover_letter"]["content"])

                jobs_payload = client.get("/api/v1/jobs", headers=self._auth_headers()).json()
                self.assertEqual(jobs_payload[0]["latest_evaluation"]["score"], 86)
                self.assertEqual(jobs_payload[0]["latest_task"]["status"], "completed")
            database.dispose()

    def test_score_task_uses_profile_fallback_for_cover_letter_identity(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            settings = self._build_settings(root)
            database = DatabaseManager(settings)
            database.create_all()
            app = create_app(
                settings,
                token_verifier=FakeTokenVerifier(),
                database_manager=database,
                evaluator_factory=lambda _root: FallbackProfileEvaluator(),
            )

            with TestClient(app) as client:
                profile_response = client.post(
                    "/api/v1/profile",
                    headers=self._auth_headers(),
                    json={
                        "display_name": "Profile Name",
                        "location": "London",
                        "resume_text": "Resume with React and TypeScript experience, but no visible contact block.",
                        "context_text": "Honest context",
                    },
                )
                self.assertEqual(profile_response.status_code, 201)

                job_response = client.post(
                    "/api/v1/jobs",
                    headers=self._auth_headers(),
                    json={
                        "company": "Lendable",
                        "role_title": "Senior React Engineer",
                        "description": "Detailed React job description.",
                    },
                )
                self.assertEqual(job_response.status_code, 201)
                job_id = job_response.json()["id"]

                response = client.post(
                    f"/api/v1/jobs/{job_id}/score",
                    headers=self._auth_headers(),
                )
                self.assertEqual(response.status_code, 202)
                task_payload = client.get(
                    f"/api/v1/tasks/{response.json()['task_id']}",
                    headers=self._auth_headers(),
                ).json()
                self.assertEqual(task_payload["status"], "completed")
            database.dispose()

    def test_retry_endpoint_recovers_failed_task_in_local_mode(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            settings = self._build_settings(root)
            database = DatabaseManager(settings)
            database.create_all()
            state = {"fail": True}

            class FlakyEvaluator(FakeEvaluator):
                def evaluate(self, resume_text: str, context_text: str, job_description: str) -> JobEvaluation:
                    if state["fail"]:
                        raise RuntimeError("temporary upstream failure")
                    return super().evaluate(resume_text, context_text, job_description)

            app = create_app(
                settings,
                token_verifier=FakeTokenVerifier(),
                database_manager=database,
                evaluator_factory=lambda _root: FlakyEvaluator(),
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
                    },
                ).json()["id"]

                task_id = client.post(
                    f"/api/v1/jobs/{job_id}/score",
                    headers=self._auth_headers(),
                ).json()["task_id"]

                failed_task = client.get(f"/api/v1/tasks/{task_id}", headers=self._auth_headers()).json()
                self.assertEqual(failed_task["status"], "failed")
                self.assertTrue(failed_task["can_retry"])
                self.assertEqual(failed_task["attempt_count"], 1)

                state["fail"] = False
                retry_response = client.post(f"/api/v1/tasks/{task_id}/retry", headers=self._auth_headers())
                self.assertEqual(retry_response.status_code, 202)
                self.assertEqual(retry_response.json()["task_id"], task_id)

                recovered_task = client.get(f"/api/v1/tasks/{task_id}", headers=self._auth_headers()).json()
                self.assertEqual(recovered_task["status"], "completed")
                self.assertEqual(recovered_task["attempt_count"], 2)
                self.assertFalse(recovered_task["can_retry"])
            database.dispose()

    def test_run_task_schedules_retry_when_redis_is_enabled(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            settings = self._build_settings(root, redis_url="redis://localhost:6379/0")
            database = DatabaseManager(settings)
            database.create_all()

            with database.session() as session:
                user = ensure_user(
                    session,
                    FakeTokenVerifier().verify_token("valid-token"),
                )
                profile_state = create_profile_state(
                    session,
                    user_id=user.id,
                    display_name="Mohammad Naderi",
                    location="London",
                    resume_text="Mohammad Naderi\nResume with React and TypeScript experience.",
                    context_text="Honest context",
                )
                job_state = create_job_state(
                    session,
                    user_id=user.id,
                    profile_id=profile_state.profile.id,
                    description="Detailed React job description.",
                    source_url=None,
                    company="Lendable",
                    role_title="Senior React Engineer",
                    location="London",
                    current_status=ApplicationStatus.WAITING,
                )
                task = create_background_task(
                    session,
                    user_id=user.id,
                    job_id=job_state.job.id,
                    task_type=BackgroundTaskType.SCORE_JOB,
                    payload={"job_id": job_state.job.id},
                )
                session.commit()
                task_id = task.id

            class AlwaysFailingEvaluator(FakeEvaluator):
                def evaluate(self, resume_text: str, context_text: str, job_description: str) -> JobEvaluation:
                    raise RuntimeError("temporary upstream failure")

            with patch("jobfit_api.task_processing.schedule_task_retry") as retry_mock:
                run_task(settings, lambda _root: AlwaysFailingEvaluator(), task_id)

            with database.session() as session:
                task = session.get(BackgroundTask, task_id)
                self.assertIsNotNone(task)
                self.assertEqual(task.status, BackgroundTaskStatus.QUEUED)
                self.assertEqual(task.attempt_count, 1)
                self.assertEqual(task.max_attempts, 3)
                self.assertIsNotNone(task.next_retry_at)
                self.assertIn("temporary upstream failure", task.error_message)

            retry_mock.assert_called_once()
            database.dispose()

    def test_cover_letter_regeneration_creates_new_cover_letter_task(self) -> None:
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
                        "resume_text": (
                            "Mohammad Naderi\n"
                            "m.n.mohammad.naderi@gmail.com\n"
                            "+44 7700 900123\n"
                            "Resume with React and TypeScript experience."
                        ),
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
                    },
                ).json()["id"]

                first_task_id = client.post(
                    f"/api/v1/jobs/{job_id}/score",
                    headers=self._auth_headers(),
                ).json()["task_id"]
                first_result = client.get(
                    f"/api/v1/tasks/{first_task_id}",
                    headers=self._auth_headers(),
                ).json()["result"]

                second_task_response = client.post(
                    f"/api/v1/jobs/{job_id}/cover-letter/regenerate",
                    headers=self._auth_headers(),
                )
                self.assertEqual(second_task_response.status_code, 202)
                second_task_id = second_task_response.json()["task_id"]

                second_task_payload = client.get(
                    f"/api/v1/tasks/{second_task_id}",
                    headers=self._auth_headers(),
                ).json()
                self.assertEqual(second_task_payload["status"], "completed")
                self.assertEqual(second_task_payload["task_type"], "generate_cover_letter")
                self.assertNotEqual(
                    second_task_payload["result"]["cover_letter_id"],
                    first_result["cover_letter_id"],
                )

                job_detail = client.get(
                    f"/api/v1/jobs/{job_id}",
                    headers=self._auth_headers(),
                ).json()
                self.assertEqual(
                    job_detail["latest_cover_letter"]["id"],
                    second_task_payload["result"]["cover_letter_id"],
                )
            database.dispose()

    def _build_settings(self, root: Path, redis_url: str | None = None) -> ApiSettings:
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
            redis_url=redis_url,
            auth_enabled=True,
            clerk_issuer="https://example.clerk.accounts.dev",
            clerk_jwks_url="https://example.clerk.accounts.dev/.well-known/jwks.json",
            clerk_audience=None,
            clerk_authorized_party=None,
        )

    def _auth_headers(self) -> dict[str, str]:
        return {"Authorization": "Bearer valid-token"}


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
