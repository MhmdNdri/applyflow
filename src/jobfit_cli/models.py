"""Compatibility exports for shared response models."""

from jobfit_core.models import (
    FallbackJobEvaluation,
    HAS_PYDANTIC,
    JobEvaluation,
    ValidationError,
    Verdict,
    job_evaluation_openai_schema,
)

__all__ = [
    "FallbackJobEvaluation",
    "HAS_PYDANTIC",
    "JobEvaluation",
    "ValidationError",
    "Verdict",
    "job_evaluation_openai_schema",
]
