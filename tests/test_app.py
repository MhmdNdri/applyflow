from __future__ import annotations

from contextlib import contextmanager
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from jobfit_cli.app import run_score, run_setup
from jobfit_cli.models import JobEvaluation
from jobfit_cli.prompts import ApplicantProfile


class FakeEvaluator:
    def __init__(self, *_args, **_kwargs) -> None:
        self.validated = False
        self.active_model = "gpt-4o-mini"

    def validate_access(self) -> None:
        self.validated = True

    def evaluate(
        self,
        resume_text: str,
        context_text: str,
        job_description: str,
    ) -> JobEvaluation:
        assert resume_text
        assert context_text
        assert job_description
        return JobEvaluation.model_validate(
            {
                "score": 74,
                "verdict": "possible_fit",
                "company": "Example Co",
                "role_title": "Platform Engineer",
                "location": "Remote",
                "source_url": None,
                "top_strengths": ["Python delivery", "API work", "Ownership"],
                "critical_gaps": ["Kubernetes depth", "GCP production", "Finance domain"],
                "feedback": "Solid software fit. Infra depth is decent. The missing GCP evidence lowers confidence.",
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
        assert resume_text
        assert context_text
        assert job_description
        assert evaluation.score == 74
        assert applicant_profile.full_name == "Mohammad Naderi"
        assert applicant_profile.email == "m.n.mohammad.naderi@gmail.com"
        assert applicant_profile.phone == "+44 7700 900123"
        assert cover_letter_date
        return (
            "Mohammad Naderi\n"
            "m.n.mohammad.naderi@gmail.com | +44 7700 900123\n"
            f"{cover_letter_date}\n\n"
            "Dear Hiring Team,\n\n"
            "I’m excited about the Platform Engineer role because it matches my work shipping "
            "Python systems, APIs, and high-ownership backend delivery.\n\n"
            "Across recent work, I’ve been most effective where product needs, technical judgment, "
            "and execution all need to stay aligned.\n\n"
            "I’d love the chance to bring that mindset to Example Co and contribute quickly.\n\n"
            "Best regards,\n"
            "Mohammad Naderi"
        )


class FakeDocsClient:
    def validate_access(self) -> None:
        return None

    def create_cover_letter_doc(self, *, title: str, content: str) -> str:
        assert "Cover Letter" in title
        assert "Platform Engineer" in title
        assert "Mohammad Naderi" in title
        assert content
        return "https://docs.google.com/document/d/example-doc/edit"


class FailingDocsClient(FakeDocsClient):
    def create_cover_letter_doc(self, *, title: str, content: str) -> str:
        raise RuntimeError("doc creation failed")


class FakeSheetsLogger:
    def __init__(self, *_args, **_kwargs) -> None:
        self.rows: list[list[str]] = []
        self.validated = False

    def validate_access(self) -> None:
        self.validated = True

    def append_row(self, row: list[str]) -> None:
        self.rows.append(row)


class FailingSheetsLogger(FakeSheetsLogger):
    def append_row(self, row: list[str]) -> None:
        raise RuntimeError("sheet append failed")


@contextmanager
def temp_cwd() -> Path:
    original = Path.cwd()
    with tempfile.TemporaryDirectory() as directory:
        os.chdir(directory)
        try:
            yield Path(directory)
        finally:
            os.chdir(original)


class AppCommandTests(unittest.TestCase):
    def test_setup_creates_templates_and_reports_missing_env(self) -> None:
        with temp_cwd() as root:
            stdout = io.StringIO()
            stderr = io.StringIO()
            with patch.dict(os.environ, {}, clear=True):
                exit_code = run_setup(root=root, stdout=stdout, stderr=stderr)

            self.assertEqual(exit_code, 1)
            self.assertTrue((root / "data" / "profile" / "resume.md").exists())
            self.assertIn("Missing OPENAI_API_KEY", stderr.getvalue())
            self.assertIn("Missing GOOGLE_SHEET_ID", stderr.getvalue())
            self.assertIn(
                "Missing GOOGLE_OAUTH_CLIENT_FILE or GOOGLE_SERVICE_ACCOUNT_FILE",
                stderr.getvalue(),
            )

    def test_setup_reports_missing_google_credentials_file(self) -> None:
        with temp_cwd() as root:
            stdout = io.StringIO()
            stderr = io.StringIO()
            with patch.dict(
                os.environ,
                {
                    "OPENAI_API_KEY": "test-key",
                    "GOOGLE_SHEET_ID": "sheet-id",
                    "GOOGLE_SERVICE_ACCOUNT_FILE": "missing/creds.json",
                },
                clear=True,
            ):
                exit_code = run_setup(
                    root=root,
                    stdout=stdout,
                    stderr=stderr,
                    evaluator_factory=lambda _config: FakeEvaluator(),
                    docs_factory=lambda _config: FakeDocsClient(),
                )

            self.assertEqual(exit_code, 1)
            self.assertIn("Google credentials file not found", stderr.getvalue())

    def test_score_persists_files_and_logs_row(self) -> None:
        sheets_instances: list[FakeSheetsLogger] = []

        def evaluator_factory(_config):
            return FakeEvaluator()

        def docs_factory(_config):
            return FakeDocsClient()

        def sheets_factory(_config):
            logger = FakeSheetsLogger()
            sheets_instances.append(logger)
            return logger

        with temp_cwd() as root:
            self._write_profile(root)
            stdout = io.StringIO()
            stderr = io.StringIO()
            with patch.dict(
                os.environ,
                {
                    "OPENAI_API_KEY": "test-key",
                    "GOOGLE_SHEET_ID": "sheet-id",
                    "GOOGLE_SERVICE_ACCOUNT_FILE": "credentials.json",
                },
                clear=True,
            ):
                exit_code = run_score(
                    root=root,
                    stdin=io.StringIO(
                        "Detailed platform engineer job description with APIs, cloud platforms, "
                        "observability, ownership expectations, stakeholder communication, and "
                        "production support responsibilities."
                    ),
                    stdout=stdout,
                    stderr=stderr,
                    evaluator_factory=evaluator_factory,
                    docs_factory=docs_factory,
                    sheets_factory=sheets_factory,
                )

            self.assertEqual(exit_code, 0)
            self.assertEqual(len(sheets_instances), 1)
            self.assertEqual(len(sheets_instances[0].rows), 1)
            self.assertEqual(sheets_instances[0].rows[0][-1], "gpt-4o-mini")
            self.assertEqual(sheets_instances[0].rows[0][3], "waiting")
            self.assertTrue(sheets_instances[0].rows[0][11].startswith("=HYPERLINK("))
            self.assertTrue(any((root / "data" / "jobs").iterdir()))
            self.assertTrue(any((root / "data" / "letters").iterdir()))
            run_files = list((root / "data" / "runs").iterdir())
            self.assertEqual(len(run_files), 1)
            run_payload = json.loads(run_files[0].read_text(encoding="utf-8"))
            self.assertEqual(run_payload["application_status"], "waiting")
            self.assertEqual(run_payload["sheet_logging"]["status"], "logged")
            self.assertEqual(run_payload["doc_logging"]["status"], "created")
            self.assertEqual(
                run_payload["cover_letter_doc_url"],
                "https://docs.google.com/document/d/example-doc/edit",
            )
            self.assertEqual(run_payload["model"], "gpt-4o-mini")
            self.assertIn("Score: 74/100", stdout.getvalue())
            self.assertIn("Cover letter doc:", stdout.getvalue())
            self.assertIn("fallback from gpt-5.4-mini", stdout.getvalue())
            self.assertIn("Evaluating job fit...", stderr.getvalue())
            self.assertIn("Generating cover letter...", stderr.getvalue())
            self.assertIn("Creating Google Doc...", stderr.getvalue())
            self.assertIn("Updating Google Sheet...", stderr.getvalue())

    def test_score_returns_partial_failure_when_doc_creation_fails(self) -> None:
        with temp_cwd() as root:
            self._write_profile(root)
            stdout = io.StringIO()
            stderr = io.StringIO()
            with patch.dict(
                os.environ,
                {
                    "OPENAI_API_KEY": "test-key",
                    "GOOGLE_SHEET_ID": "sheet-id",
                    "GOOGLE_SERVICE_ACCOUNT_FILE": "credentials.json",
                },
                clear=True,
            ):
                exit_code = run_score(
                    root=root,
                    stdin=io.StringIO(
                        "Detailed platform engineer job description with APIs, cloud platforms, "
                        "observability, ownership expectations, stakeholder communication, and "
                        "production support responsibilities."
                    ),
                    stdout=stdout,
                    stderr=stderr,
                    evaluator_factory=lambda _config: FakeEvaluator(),
                    docs_factory=lambda _config: FailingDocsClient(),
                    sheets_factory=lambda _config: FakeSheetsLogger(),
                )

            self.assertEqual(exit_code, 2)
            run_files = list((root / "data" / "runs").iterdir())
            run_payload = json.loads(run_files[0].read_text(encoding="utf-8"))
            self.assertEqual(run_payload["doc_logging"]["status"], "failed")
            self.assertEqual(run_payload["sheet_logging"]["status"], "pending")
            self.assertTrue(any((root / "data" / "letters").iterdir()))
            self.assertIn("Google Doc creation failed", stderr.getvalue())
            self.assertIn("Cover letter backup:", stdout.getvalue())

    def test_score_returns_partial_failure_when_sheet_logging_fails(self) -> None:
        def evaluator_factory(_config):
            return FakeEvaluator()

        with temp_cwd() as root:
            self._write_profile(root)
            stdout = io.StringIO()
            stderr = io.StringIO()
            with patch.dict(
                os.environ,
                {
                    "OPENAI_API_KEY": "test-key",
                    "GOOGLE_SHEET_ID": "sheet-id",
                    "GOOGLE_SERVICE_ACCOUNT_FILE": "credentials.json",
                },
                clear=True,
            ):
                exit_code = run_score(
                    root=root,
                    stdin=io.StringIO("Detailed job description with several required technologies."),
                    stdout=stdout,
                    stderr=stderr,
                    evaluator_factory=evaluator_factory,
                    docs_factory=lambda _config: FakeDocsClient(),
                    sheets_factory=lambda _config: FailingSheetsLogger(),
                )

            self.assertEqual(exit_code, 2)
            run_files = list((root / "data" / "runs").iterdir())
            run_payload = json.loads(run_files[0].read_text(encoding="utf-8"))
            self.assertEqual(run_payload["sheet_logging"]["status"], "failed")
            self.assertEqual(run_payload["doc_logging"]["status"], "created")
            self.assertIn("Google Sheets logging failed", stderr.getvalue())
            self.assertIn("Run record:", stdout.getvalue())

    def test_score_warns_for_sparse_job_description(self) -> None:
        with temp_cwd() as root:
            self._write_profile(root)
            stderr = io.StringIO()
            with patch.dict(
                os.environ,
                {
                    "OPENAI_API_KEY": "test-key",
                    "GOOGLE_SHEET_ID": "sheet-id",
                    "GOOGLE_SERVICE_ACCOUNT_FILE": "credentials.json",
                },
                clear=True,
            ):
                run_score(
                    root=root,
                    stdin=io.StringIO("Backend engineer."),
                    stdout=io.StringIO(),
                    stderr=stderr,
                    evaluator_factory=lambda _config: FakeEvaluator(),
                    docs_factory=lambda _config: FakeDocsClient(),
                    sheets_factory=lambda _config: FakeSheetsLogger(),
                )

            self.assertIn("sparse", stderr.getvalue().lower())

    def _write_profile(self, root: Path) -> None:
        profile_dir = root / "data" / "profile"
        profile_dir.mkdir(parents=True, exist_ok=True)
        (profile_dir / "resume.md").write_text(
            (
                "Mohammad Naderi\n"
                "m.n.mohammad.naderi@gmail.com\n"
                "+44 7700 900123\n"
                "Backend engineer with Python and API delivery experience.\n"
            ),
            encoding="utf-8",
        )
        (profile_dir / "context.md").write_text("Context content", encoding="utf-8")


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
