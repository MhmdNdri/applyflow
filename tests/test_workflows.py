from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo
import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from jobfit_core.models import JobEvaluation
from jobfit_core.prompts import ApplicantProfile
from jobfit_core.workflows import (
    JobApplicationService,
    build_cover_letter_title,
    normalize_evaluation,
    verdict_value,
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
        assert resume_text
        assert context_text
        assert job_description
        return JobEvaluation.model_validate(
            {
                "score": 83,
                "verdict": "strong_fit",
                "company": "Acme",
                "role_title": "Platform Engineer",
                "location": "Remote",
                "source_url": None,
                "top_strengths": ["Python", "APIs", "Delivery"],
                "critical_gaps": ["Kubernetes", "GCP", "Finance"],
                "feedback": "Strong fit with a few infrastructure gaps.",
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
        assert evaluation.score == 83
        assert applicant_profile.full_name == "Mohammad Naderi"
        assert cover_letter_date == "27 March 2026"
        return (
            "27 March 2026\n\n"
            "Dear Hiring Team,\n\n"
            "Paragraph one.\n\n"
            "Paragraph two.\n\n"
            "Paragraph three.\n\n"
            "Best regards,\n"
            "Mohammad Naderi"
        )


class WorkflowTests(unittest.TestCase):
    def test_job_application_service_scores_and_generates_letter(self) -> None:
        messages: list[str] = []
        service = JobApplicationService(FakeEvaluator())

        artifacts = service.score_job(
            resume_text=(
                "Mohammad Naderi\n"
                "m.n.mohammad.naderi@gmail.com\n"
                "+44 7700 900123\n"
                "Backend engineer with Python delivery experience."
            ),
            context_text="Honest context",
            job_description="Detailed platform job description",
            now=datetime(2026, 3, 27, 9, 30, tzinfo=ZoneInfo("Europe/London")),
            progress=messages.append,
        )

        self.assertEqual(artifacts.evaluation.score, 83)
        self.assertEqual(artifacts.cover_letter_date, "27 March 2026")
        self.assertEqual(artifacts.applicant_profile.full_name, "Mohammad Naderi")
        self.assertEqual(artifacts.model_used, "gpt-4o-mini")
        self.assertIn("Best regards,\nMohammad Naderi", artifacts.cover_letter)
        self.assertEqual(messages, ["Evaluating job fit...", "Generating cover letter..."])

    def test_workflow_helpers_return_api_friendly_values(self) -> None:
        evaluation = JobEvaluation.model_validate(
            {
                "score": 83,
                "verdict": "strong_fit",
                "company": "Acme",
                "role_title": "Platform Engineer",
                "location": "Remote",
                "source_url": None,
                "top_strengths": ["Python", "APIs", "Delivery"],
                "critical_gaps": ["Kubernetes", "GCP", "Finance"],
                "feedback": "Strong fit with a few infrastructure gaps.",
            }
        )

        self.assertEqual(verdict_value(evaluation), "strong_fit")
        self.assertEqual(normalize_evaluation(evaluation)["verdict"], "strong_fit")
        self.assertEqual(
            build_cover_letter_title(
                human_date="27 March 2026",
                applicant_name="Mohammad Naderi",
                company="Acme",
                role_title="Platform Engineer",
            ),
            "27 March 2026 - Mohammad Naderi - Platform Engineer - Acme Cover Letter",
        )


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
