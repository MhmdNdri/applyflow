from __future__ import annotations

import base64
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
from sqlalchemy import select

from jobfit_api.auth import AuthContext, AuthenticationError, TokenVerifier
from jobfit_api.database import DatabaseManager
from jobfit_api.main import create_app
from jobfit_api.models import BackgroundTask, BackgroundTaskStatus, BackgroundTaskType, ResumeVersion, User
from jobfit_api.settings import ApiSettings


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


class PhaseThreeApiTests(unittest.TestCase):
    def test_profile_and_jobs_crud_flow(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            settings = self._build_settings(root)
            database = DatabaseManager(settings)
            database.create_all()
            app = create_app(settings, token_verifier=FakeTokenVerifier(), database_manager=database)

            with TestClient(app) as client:
                response = client.post(
                    "/api/v1/profile",
                    headers=self._auth_headers(),
                    json={
                        "display_name": "Mohammad Naderi",
                        "location": "London",
                        "resume_text": "Resume v1",
                        "context_text": "Context v1",
                    },
                )
                self.assertEqual(response.status_code, 201)
                profile_payload = response.json()
                self.assertEqual(profile_payload["resume_version_number"], 1)
                self.assertEqual(profile_payload["context_version_number"], 1)

                response = client.get("/api/v1/profile", headers=self._auth_headers())
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json()["display_name"], "Mohammad Naderi")

                response = client.patch(
                    "/api/v1/profile",
                    headers=self._auth_headers(),
                    json={
                        "location": "London, UK",
                        "resume_text": "Resume v2",
                    },
                )
                self.assertEqual(response.status_code, 200)
                updated_profile = response.json()
                self.assertEqual(updated_profile["resume_version_number"], 2)
                self.assertEqual(updated_profile["context_version_number"], 1)
                self.assertEqual(updated_profile["location"], "London, UK")

                response = client.post(
                    "/api/v1/jobs",
                    headers=self._auth_headers(),
                    json={
                        "company": "Lendable",
                        "role_title": "Senior React Engineer",
                        "location": "London, UK",
                        "description": "Detailed customer-facing React job description.",
                    },
                )
                self.assertEqual(response.status_code, 201)
                job_payload = response.json()
                job_id = job_payload["id"]
                self.assertEqual(job_payload["company"], "Lendable")
                self.assertEqual(job_payload["current_status"], "waiting")
                self.assertEqual(len(job_payload["status_history"]), 1)
                self.assertEqual(job_payload["status_history"][0]["next_status"], "waiting")
                self.assertEqual(job_payload["profile_id"], profile_payload["id"])

                response = client.get("/api/v1/jobs", headers=self._auth_headers())
                self.assertEqual(response.status_code, 200)
                jobs_payload = response.json()
                self.assertEqual(len(jobs_payload), 1)
                self.assertEqual(jobs_payload[0]["id"], job_id)

                response = client.patch(
                    f"/api/v1/jobs/{job_id}",
                    headers=self._auth_headers(),
                    json={
                        "location": "Remote, UK",
                        "source_url": "https://example.com/job",
                    },
                )
                self.assertEqual(response.status_code, 200)
                updated_job = response.json()
                self.assertEqual(updated_job["location"], "Remote, UK")
                self.assertEqual(updated_job["source_url"], "https://example.com/job")

                response = client.patch(
                    f"/api/v1/jobs/{job_id}/status",
                    headers=self._auth_headers(),
                    json={"status": "interviewing"},
                )
                self.assertEqual(response.status_code, 200)
                status_payload = response.json()
                self.assertEqual(status_payload["current_status"], "interviewing")
                self.assertEqual(len(status_payload["status_history"]), 2)
                self.assertEqual(status_payload["status_history"][1]["previous_status"], "waiting")
                self.assertEqual(status_payload["status_history"][1]["next_status"], "interviewing")

                response = client.get(f"/api/v1/jobs/{job_id}", headers=self._auth_headers())
                self.assertEqual(response.status_code, 200)
                detail_payload = response.json()
                self.assertEqual(detail_payload["current_status"], "interviewing")
                self.assertEqual(len(detail_payload["status_history"]), 2)
            database.dispose()

    def test_task_lookup_returns_owned_task(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            settings = self._build_settings(root)
            database = DatabaseManager(settings)
            database.create_all()
            app = create_app(settings, token_verifier=FakeTokenVerifier(), database_manager=database)

            with TestClient(app) as client:
                response = client.post(
                    "/api/v1/jobs",
                    headers=self._auth_headers(),
                    json={
                        "company": "Acme",
                        "role_title": "Backend Engineer",
                        "description": "Detailed backend job description.",
                    },
                )
                self.assertEqual(response.status_code, 201)
                job_id = response.json()["id"]

                with database.session() as session:
                    user = session.scalar(select(User).where(User.clerk_user_id == "clerk_user_123"))
                    self.assertIsNotNone(user)
                    task = BackgroundTask(
                        user_id=user.id,
                        job_id=job_id,
                        task_type=BackgroundTaskType.SCORE_JOB,
                        status=BackgroundTaskStatus.QUEUED,
                        payload={"job_id": job_id},
                        result=None,
                    )
                    session.add(task)
                    session.commit()
                    task_id = task.id

                response = client.get(f"/api/v1/tasks/{task_id}", headers=self._auth_headers())
                self.assertEqual(response.status_code, 200)
                payload = response.json()
                self.assertEqual(payload["task_type"], "score_job")
                self.assertEqual(payload["status"], "queued")
                self.assertEqual(payload["job_id"], job_id)
                self.assertEqual(payload["payload"], {"job_id": job_id})
            database.dispose()

    def test_profile_supports_uploaded_resume_and_context_files(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            settings = self._build_settings(root)
            database = DatabaseManager(settings)
            database.create_all()
            app = create_app(settings, token_verifier=FakeTokenVerifier(), database_manager=database)

            with TestClient(app) as client:
                response = client.post(
                    "/api/v1/profile",
                    headers=self._auth_headers(),
                    json={
                        "display_name": "Mohammad Naderi",
                        "location": "London",
                        "resume_upload": {
                            "file_name": "resume.txt",
                            "content_type": "text/plain",
                            "content_base64": base64.b64encode(b"Resume from file").decode("ascii"),
                        },
                        "context_upload": {
                            "file_name": "context.md",
                            "content_type": "text/markdown",
                            "content_base64": base64.b64encode(b"Context from file").decode("ascii"),
                        },
                    },
                )
                self.assertEqual(response.status_code, 201)
                payload = response.json()
                self.assertEqual(payload["resume_text"], "Resume from file")
                self.assertEqual(payload["context_text"], "Context from file")
                self.assertEqual(payload["resume_source_file"]["file_name"], "resume.txt")
                self.assertEqual(payload["context_source_file"]["file_name"], "context.md")

                with database.session() as session:
                    version = session.scalar(select(ResumeVersion).where(ResumeVersion.profile_id == payload["id"]))
                    self.assertIsNotNone(version)
                    self.assertEqual(version.source_file_name, "resume.txt")
                    self.assertEqual(version.source_file_bytes, b"Resume from file")
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


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
