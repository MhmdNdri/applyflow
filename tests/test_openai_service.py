from __future__ import annotations

import json
import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from jobfit_cli.models import JobEvaluation
from jobfit_cli.openai_service import OpenAIEvaluator
from jobfit_cli.prompts import ApplicantProfile


class FakeResponse:
    output_text = "OK"
    output = []


class FakeModelError(Exception):
    def __init__(self, message: str, *, status_code: int = 403, code: str = "model_not_found") -> None:
        super().__init__(message)
        self.status_code = status_code
        self.body = {"error": {"message": message, "code": code}}


class FakeResponsesAPI:
    def __init__(self, scripted_results=None) -> None:
        self.calls: list[dict[str, object]] = []
        self.scripted_results = list(scripted_results or [])

    def create(self, **kwargs):
        self.calls.append(kwargs)
        if self.scripted_results:
            result = self.scripted_results.pop(0)
            if isinstance(result, Exception):
                raise result
            return result
        return FakeResponse()


class FakeClient:
    def __init__(self, responses_api: FakeResponsesAPI | None = None) -> None:
        self.responses = responses_api or FakeResponsesAPI()


class OpenAIServiceTests(unittest.TestCase):
    def test_validate_access_uses_supported_minimum_output_tokens(self) -> None:
        evaluator = OpenAIEvaluator(api_key="test-key", model="gpt-5.4-mini")
        fake_client = FakeClient()
        evaluator._client = fake_client

        evaluator.validate_access()

        self.assertEqual(len(fake_client.responses.calls), 1)
        self.assertEqual(fake_client.responses.calls[0]["max_output_tokens"], 16)
        self.assertEqual(fake_client.responses.calls[0]["model"], "gpt-5.4-mini")

    def test_validate_access_falls_back_when_primary_model_is_unavailable(self) -> None:
        responses_api = FakeResponsesAPI(
            scripted_results=[
                FakeModelError("Project does not have access to model `gpt-5.4-mini`"),
                FakeResponse(),
            ]
        )
        evaluator = OpenAIEvaluator(api_key="test-key", model="gpt-5.4-mini")
        evaluator._client = FakeClient(responses_api)

        evaluator.validate_access()

        self.assertEqual(
            [call["model"] for call in responses_api.calls],
            ["gpt-5.4-mini", "gpt-4o-mini"],
        )
        self.assertEqual(evaluator.active_model, "gpt-4o-mini")

    def test_generate_cover_letter_returns_plain_text(self) -> None:
        class CoverLetterResponse:
            output_text = "First paragraph.\n\nSecond paragraph.\n\nThird paragraph."
            output = []

        responses_api = FakeResponsesAPI(scripted_results=[CoverLetterResponse()])
        evaluator = OpenAIEvaluator(api_key="test-key", model="gpt-5.4-mini")
        evaluator._client = FakeClient(responses_api)

        cover_letter = evaluator.generate_cover_letter(
            resume_text="resume",
            context_text="context",
            job_description="job",
            evaluation=JobEvaluation.model_validate(
                {
                    "score": 75,
                    "verdict": "possible_fit",
                    "company": "Acme",
                    "role_title": "Platform Engineer",
                    "location": None,
                    "source_url": None,
                    "top_strengths": ["Python", "APIs", "Ownership"],
                    "critical_gaps": ["Kubernetes", "GCP", "Finance"],
                    "feedback": "Solid fit with a few gaps.",
                }
            ),
            applicant_profile=ApplicantProfile(
                full_name="Mohammad Naderi",
                email="m.n.mohammad.naderi@gmail.com",
                phone="+44 7700 900123",
            ),
            cover_letter_date="27 March 2026",
        )

        self.assertEqual(
            cover_letter,
            (
                "27 March 2026\n\n"
                "Dear Hiring Team,\n\n"
                "First paragraph.\n\n"
                "Second paragraph.\n\n"
                "Third paragraph.\n\n"
                "Best regards,\n"
                "Mohammad Naderi"
            ),
        )

    def test_generate_cover_letter_trims_overlong_body_to_one_page_range(self) -> None:
        class CoverLetterResponse:
            output_text = (
                ("First paragraph sentence with relevant experience and product ownership. " * 12)
                + "\n\n"
                + ("Second paragraph sentence with architecture, performance, and collaboration. " * 12)
                + "\n\n"
                + ("Third paragraph sentence with motivation, alignment, and delivery mindset. " * 12)
            )
            output = []

        responses_api = FakeResponsesAPI(scripted_results=[CoverLetterResponse()])
        evaluator = OpenAIEvaluator(api_key="test-key", model="gpt-5.4-mini")
        evaluator._client = FakeClient(responses_api)

        cover_letter = evaluator.generate_cover_letter(
            resume_text="resume",
            context_text="context",
            job_description="job",
            evaluation=JobEvaluation.model_validate(
                {
                    "score": 75,
                    "verdict": "possible_fit",
                    "company": "Acme",
                    "role_title": "Platform Engineer",
                    "location": None,
                    "source_url": None,
                    "top_strengths": ["Python", "APIs", "Ownership"],
                    "critical_gaps": ["Kubernetes", "GCP", "Finance"],
                    "feedback": "Solid fit with a few gaps.",
                }
            ),
            applicant_profile=ApplicantProfile(
                full_name="Mohammad Naderi",
                email="m.n.mohammad.naderi@gmail.com",
                phone="+44 7700 900123",
            ),
            cover_letter_date="27 March 2026",
        )

        body = cover_letter.split("Dear Hiring Team,\n\n", maxsplit=1)[1].split(
            "\n\nBest regards,",
            maxsplit=1,
        )[0]
        self.assertLessEqual(len(body.split()), 210)

    def test_evaluate_sanitizes_common_schema_issues_without_repair_call(self) -> None:
        class EvaluationResponse:
            output_text = json.dumps(
                {
                    "score": 75,
                    "verdict": "possible_fit",
                    "company": " Acme ",
                    "role_title": "Platform Engineer",
                    "location": None,
                    "source_url": None,
                    "top_strengths": ["Python", "APIs", "Ownership", "Extra"],
                    "critical_gaps": ["Kubernetes", "GCP", "Finance", "Another"],
                    "feedback": "One. Two. Three. Four. Five.",
                }
            )
            output = []

        responses_api = FakeResponsesAPI(scripted_results=[EvaluationResponse()])
        evaluator = OpenAIEvaluator(api_key="test-key", model="gpt-5.4-mini")
        evaluator._client = FakeClient(responses_api)

        evaluation = evaluator.evaluate(
            resume_text="resume",
            context_text="context",
            job_description="job",
        )

        self.assertEqual(evaluation.company, "Acme")
        self.assertEqual(evaluation.top_strengths, ["Python", "APIs", "Ownership"])
        self.assertEqual(evaluation.critical_gaps, ["Kubernetes", "GCP", "Finance"])
        self.assertEqual(evaluation.feedback, "One. Two. Three. Four.")
        self.assertEqual(len(responses_api.calls), 1)

    def test_evaluate_repairs_payload_when_schema_is_still_invalid(self) -> None:
        class InvalidEvaluationResponse:
            output_text = json.dumps(
                {
                    "score": 75,
                    "verdict": "possible_fit",
                    "company": "Acme",
                    "role_title": "Platform Engineer",
                    "location": None,
                    "source_url": None,
                    "top_strengths": ["Python", "APIs"],
                    "critical_gaps": ["Kubernetes"],
                    "feedback": "Solid fit.",
                }
            )
            output = []

        class RepairedEvaluationResponse:
            output_text = json.dumps(
                {
                    "score": 75,
                    "verdict": "possible_fit",
                    "company": "Acme",
                    "role_title": "Platform Engineer",
                    "location": None,
                    "source_url": None,
                    "top_strengths": ["Python", "APIs", "Ownership"],
                    "critical_gaps": ["Kubernetes", "GCP", "Finance"],
                    "feedback": "Solid fit. Cloud depth is thinner. Platform ownership is relevant.",
                }
            )
            output = []

        responses_api = FakeResponsesAPI(
            scripted_results=[InvalidEvaluationResponse(), RepairedEvaluationResponse()]
        )
        evaluator = OpenAIEvaluator(api_key="test-key", model="gpt-5.4-mini")
        evaluator._client = FakeClient(responses_api)

        evaluation = evaluator.evaluate(
            resume_text="resume",
            context_text="context",
            job_description="job",
        )

        self.assertEqual(evaluation.top_strengths, ["Python", "APIs", "Ownership"])
        self.assertEqual(evaluation.critical_gaps, ["Kubernetes", "GCP", "Finance"])
        self.assertEqual(len(responses_api.calls), 2)
        self.assertEqual(
            responses_api.calls[1]["text"]["format"]["name"],
            "job_fit_evaluation_repair",
        )


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
