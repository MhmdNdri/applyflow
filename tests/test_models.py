from __future__ import annotations

import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from jobfit_cli.models import JobEvaluation, ValidationError, job_evaluation_openai_schema
from jobfit_api.models import ApplicationStatus, BackgroundTaskStatus, BackgroundTaskType, EvaluationVerdict, db_enum


class JobEvaluationTests(unittest.TestCase):
    def test_openai_schema_requires_all_properties(self) -> None:
        schema = job_evaluation_openai_schema()

        self.assertEqual(
            set(schema["required"]),
            set(schema["properties"].keys()),
        )
        self.assertEqual(schema["properties"]["company"]["type"], ["string", "null"])
        self.assertEqual(schema["properties"]["top_strengths"]["minItems"], 3)
        self.assertEqual(schema["properties"]["top_strengths"]["maxItems"], 3)

    def test_valid_payload_passes_validation(self) -> None:
        evaluation = JobEvaluation.model_validate(
            {
                "score": 82,
                "verdict": "possible_fit",
                "company": "Acme",
                "role_title": "Backend Engineer",
                "location": None,
                "source_url": "https://example.com/jobs/1",
                "top_strengths": ["Python", "APIs", "Ownership"],
                "critical_gaps": ["Kubernetes", "GCP", "Hiring domain depth"],
                "feedback": "Strong backend match. Platform depth is good. GCP is a real gap.",
            }
        )

        self.assertEqual(evaluation.score, 82)
        self.assertEqual(
            getattr(evaluation.verdict, "value", evaluation.verdict),
            "possible_fit",
        )

    def test_invalid_score_is_rejected(self) -> None:
        with self.assertRaises(ValidationError):
            JobEvaluation.model_validate(
                {
                    "score": 101,
                    "verdict": "possible_fit",
                    "company": None,
                    "role_title": None,
                    "location": None,
                    "source_url": None,
                    "top_strengths": ["A", "B", "C"],
                    "critical_gaps": ["A", "B", "C"],
                    "feedback": "Too high.",
                }
            )

    def test_malformed_triplets_are_rejected(self) -> None:
        with self.assertRaises(ValidationError):
            JobEvaluation.model_validate(
                {
                    "score": 40,
                    "verdict": "weak_fit",
                    "company": None,
                    "role_title": None,
                    "location": None,
                    "source_url": None,
                    "top_strengths": ["Only one"],
                    "critical_gaps": ["A", "B", "C"],
                    "feedback": "Short summary.",
                }
            )

    def test_feedback_longer_than_four_sentences_is_rejected(self) -> None:
        with self.assertRaises(ValidationError):
            JobEvaluation.model_validate(
                {
                    "score": 20,
                    "verdict": "not_fit",
                    "company": None,
                    "role_title": None,
                    "location": None,
                    "source_url": None,
                    "top_strengths": ["A", "B", "C"],
                    "critical_gaps": ["D", "E", "F"],
                    "feedback": "One. Two. Three. Four. Five.",
                }
            )


class ApiEnumModelTests(unittest.TestCase):
    def test_database_enums_store_values_not_python_member_names(self) -> None:
        application_status = db_enum(ApplicationStatus, name="application_status")
        evaluation_verdict = db_enum(EvaluationVerdict, name="evaluation_verdict")
        task_type = db_enum(BackgroundTaskType, name="background_task_type")
        task_status = db_enum(BackgroundTaskStatus, name="background_task_status")

        self.assertEqual(application_status.enums, [status.value for status in ApplicationStatus])
        self.assertEqual(evaluation_verdict.enums, [verdict.value for verdict in EvaluationVerdict])
        self.assertEqual(task_type.enums, [task.value for task in BackgroundTaskType])
        self.assertEqual(task_status.enums, [status.value for status in BackgroundTaskStatus])


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
