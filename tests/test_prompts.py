from __future__ import annotations

import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from jobfit_cli.models import JobEvaluation
from jobfit_cli.prompts import (
    ApplicantProfile,
    build_cover_letter_input,
    build_job_fit_input,
    extract_applicant_profile,
    infer_name_from_email,
)


class PromptTests(unittest.TestCase):
    def test_prompt_contains_profile_sections_in_order(self) -> None:
        prompt = build_job_fit_input(
            resume_text="resume body",
            context_text="context body",
            job_description="job body",
        )

        self.assertLess(prompt.index("Candidate Resume:"), prompt.index("Candidate Honest Context:"))
        self.assertLess(prompt.index("Candidate Honest Context:"), prompt.index("Job Description:"))
        self.assertIn("resume body", prompt)
        self.assertIn("context body", prompt)
        self.assertIn("job body", prompt)

    def test_cover_letter_prompt_includes_fit_summary(self) -> None:
        evaluation = JobEvaluation.model_validate(
            {
                "score": 81,
                "verdict": "strong_fit",
                "company": "Acme",
                "role_title": "Backend Engineer",
                "location": None,
                "source_url": None,
                "top_strengths": ["Python", "APIs", "Delivery"],
                "critical_gaps": ["Kubernetes", "GCP", "Finance"],
                "feedback": "Strong fit with a few platform gaps.",
            }
        )

        prompt = build_cover_letter_input(
            resume_text="resume body",
            context_text="context body",
            job_description="job body",
            evaluation=evaluation,
            applicant_profile=ApplicantProfile(
                full_name="Mohammad Naderi",
                email="m.n.mohammad.naderi@gmail.com",
                phone="+44 7700 900123",
            ),
            cover_letter_date="27 March 2026",
        )

        self.assertIn("Fit Summary:", prompt)
        self.assertIn("Score: 81/100", prompt)
        self.assertIn("Top Strengths: Python; APIs; Delivery", prompt)
        self.assertIn("Critical Gaps: Kubernetes; GCP; Finance", prompt)
        self.assertIn("Mohammad Naderi", prompt)
        self.assertIn("m.n.mohammad.naderi@gmail.com", prompt)
        self.assertIn("27 March 2026", prompt)
        self.assertIn("Best regards,", prompt)
        self.assertIn("Write only the 3 body paragraphs", prompt)
        self.assertIn("150 to 210 words", prompt)
        self.assertIn("one page", prompt)

    def test_extract_applicant_profile_finds_name_email_and_phone(self) -> None:
        profile = extract_applicant_profile(
            (
                "Mohammad Naderi\n"
                "m.n.mohammad.naderi@gmail.com\n"
                "+44 7700 900123\n"
                "Backend engineer focused on Python systems.\n"
            )
        )

        self.assertEqual(profile.full_name, "Mohammad Naderi")
        self.assertEqual(profile.email, "m.n.mohammad.naderi@gmail.com")
        self.assertEqual(profile.phone, "+44 7700 900123")

    def test_infer_name_from_email_uses_last_meaningful_chunks(self) -> None:
        self.assertEqual(
            infer_name_from_email("m.n.mohammad.naderi@gmail.com"),
            "Mohammad Naderi",
        )


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
