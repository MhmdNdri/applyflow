"""Typed response models."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
import re
from typing import Any

try:
    from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator
except ImportError:  # pragma: no cover - exercised via fallback tests instead
    BaseModel = object  # type: ignore[assignment]
    ConfigDict = None  # type: ignore[assignment]
    Field = None  # type: ignore[assignment]
    ValidationError = ValueError  # type: ignore[assignment]
    field_validator = None  # type: ignore[assignment]
    HAS_PYDANTIC = False
else:
    HAS_PYDANTIC = True


class Verdict(str, Enum):
    STRONG_FIT = "strong_fit"
    POSSIBLE_FIT = "possible_fit"
    WEAK_FIT = "weak_fit"
    NOT_FIT = "not_fit"


def job_evaluation_openai_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "score": {"type": "integer", "minimum": 0, "maximum": 100},
            "verdict": {
                "type": "string",
                "enum": [item.value for item in Verdict],
            },
            "company": {"type": ["string", "null"]},
            "role_title": {"type": ["string", "null"]},
            "location": {"type": ["string", "null"]},
            "source_url": {"type": ["string", "null"]},
            "top_strengths": {
                "type": "array",
                "items": {"type": "string"},
                "minItems": 3,
                "maxItems": 3,
            },
            "critical_gaps": {
                "type": "array",
                "items": {"type": "string"},
                "minItems": 3,
                "maxItems": 3,
            },
            "feedback": {"type": "string"},
        },
        "required": [
            "score",
            "verdict",
            "company",
            "role_title",
            "location",
            "source_url",
            "top_strengths",
            "critical_gaps",
            "feedback",
        ],
    }


def _normalize_optional_text(value: Any) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError("optional fields must be strings or null")

    normalized = value.strip()
    return normalized or None


def _validate_string_triplet(field_name: str, value: Any) -> list[str]:
    if not isinstance(value, list):
        raise ValueError(f"{field_name} must be a list")
    if len(value) != 3:
        raise ValueError(f"{field_name} must contain exactly 3 items")

    normalized: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise ValueError(f"{field_name} items must be non-empty strings")
        normalized.append(item.strip())

    return normalized


def _validate_feedback(value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("feedback must be a non-empty string")

    normalized = value.strip()
    sentence_count = len([part for part in re.split(r"[.!?]+", normalized) if part.strip()])
    if sentence_count > 4:
        raise ValueError("feedback must contain at most 4 sentences")
    return normalized


def _manual_validate(payload: dict[str, Any]) -> "FallbackJobEvaluation":
    allowed_keys = {
        "score",
        "verdict",
        "company",
        "role_title",
        "location",
        "source_url",
        "top_strengths",
        "critical_gaps",
        "feedback",
    }
    extra_keys = set(payload) - allowed_keys
    if extra_keys:
        raise ValueError(f"unexpected keys: {sorted(extra_keys)}")

    score = payload.get("score")
    if not isinstance(score, int) or not 0 <= score <= 100:
        raise ValueError("score must be an integer between 0 and 100")

    verdict = payload.get("verdict")
    valid_verdicts = {item.value for item in Verdict}
    if verdict not in valid_verdicts:
        raise ValueError(f"verdict must be one of {sorted(valid_verdicts)}")

    return FallbackJobEvaluation(
        score=score,
        verdict=verdict,
        company=_normalize_optional_text(payload.get("company")),
        role_title=_normalize_optional_text(payload.get("role_title")),
        location=_normalize_optional_text(payload.get("location")),
        source_url=_normalize_optional_text(payload.get("source_url")),
        top_strengths=_validate_string_triplet("top_strengths", payload.get("top_strengths")),
        critical_gaps=_validate_string_triplet("critical_gaps", payload.get("critical_gaps")),
        feedback=_validate_feedback(payload.get("feedback")),
    )


@dataclass(slots=True)
class FallbackJobEvaluation:
    score: int
    verdict: str
    company: str | None
    role_title: str | None
    location: str | None
    source_url: str | None
    top_strengths: list[str]
    critical_gaps: list[str]
    feedback: str

    @classmethod
    def model_validate(cls, payload: dict[str, Any]) -> "FallbackJobEvaluation":
        return _manual_validate(payload)

    @classmethod
    def model_json_schema(cls) -> dict[str, Any]:
        return job_evaluation_openai_schema()

    def model_dump(self) -> dict[str, Any]:
        return asdict(self)


if HAS_PYDANTIC:

    class JobEvaluation(BaseModel):
        model_config = ConfigDict(extra="forbid")

        score: int = Field(ge=0, le=100)
        verdict: Verdict
        company: str | None = None
        role_title: str | None = None
        location: str | None = None
        source_url: str | None = None
        top_strengths: list[str]
        critical_gaps: list[str]
        feedback: str

        @field_validator("company", "role_title", "location", "source_url", mode="before")
        @classmethod
        def normalize_optional_text(cls, value: Any) -> str | None:
            return _normalize_optional_text(value)

        @field_validator("top_strengths", "critical_gaps")
        @classmethod
        def validate_triplets(cls, value: Any, info: Any) -> list[str]:
            return _validate_string_triplet(info.field_name, value)

        @field_validator("feedback")
        @classmethod
        def validate_feedback(cls, value: Any) -> str:
            return _validate_feedback(value)

else:
    JobEvaluation = FallbackJobEvaluation
