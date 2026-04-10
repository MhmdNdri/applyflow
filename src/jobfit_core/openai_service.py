"""OpenAI integration shared across interfaces."""

from __future__ import annotations

import json
import re
from typing import Any

from jobfit_cli.config import ConfigurationError

from .models import JobEvaluation, ValidationError, job_evaluation_openai_schema
from .prompts import (
    ApplicantProfile,
    COVER_LETTER_SYSTEM_PROMPT,
    EVALUATION_SYSTEM_PROMPT,
    REPAIR_SYSTEM_PROMPT,
    build_cover_letter_input,
    build_job_fit_input,
    build_job_fit_repair_input,
)


class OpenAIValidationError(RuntimeError):
    """Raised when OpenAI configuration or responses are invalid."""


class ModelRefusalError(OpenAIValidationError):
    """Raised when the model refuses the request."""


MAX_COVER_LETTER_BODY_WORDS = 210
DEFAULT_OPENAI_MODEL = "gpt-5.4-mini"
OPENAI_MODEL_FALLBACK = "gpt-4o-mini"


class OpenAIEvaluator:
    def __init__(
        self,
        api_key: str,
        model: str,
        fallback_model: str | None = OPENAI_MODEL_FALLBACK,
    ) -> None:
        self.api_key = api_key
        self.requested_model = model
        self.fallback_model = fallback_model
        self.active_model = model
        self._client = None

    @property
    def client(self) -> Any:
        if self._client is not None:
            return self._client

        try:
            from openai import OpenAI
        except ImportError as exc:  # pragma: no cover - depends on local environment
            raise ConfigurationError(
                "The `openai` package is not installed. Run `pip install -e .` first."
            ) from exc

        self._client = OpenAI(api_key=self.api_key)
        return self._client

    def validate_access(self) -> None:
        response = self._create_response(
            instructions="Reply with OK.",
            input="Reply with OK.",
            max_output_tokens=16,
        )
        output_text = extract_output_text(response)
        if not output_text:
            refusal = extract_refusal_text(response)
            if refusal:
                raise ModelRefusalError(refusal)
            raise OpenAIValidationError("OpenAI validation returned no text output.")

    def evaluate(
        self,
        resume_text: str,
        context_text: str,
        job_description: str,
    ) -> JobEvaluation:
        response = self._create_response(
            instructions=EVALUATION_SYSTEM_PROMPT,
            input=build_job_fit_input(resume_text, context_text, job_description),
            text={
                "format": {
                    "type": "json_schema",
                    "name": "job_fit_evaluation",
                    "strict": True,
                    "schema": job_evaluation_openai_schema(),
                }
            },
            max_output_tokens=600,
        )
        refusal = extract_refusal_text(response)
        if refusal:
            raise ModelRefusalError(refusal)

        output_text = extract_output_text(response)
        if not output_text:
            raise OpenAIValidationError("OpenAI returned no structured output.")

        try:
            payload = json.loads(output_text)
        except json.JSONDecodeError as exc:
            raise OpenAIValidationError("OpenAI returned invalid JSON output.") from exc

        return self._validate_or_repair_evaluation(payload)

    def generate_cover_letter(
        self,
        resume_text: str,
        context_text: str,
        job_description: str,
        evaluation: JobEvaluation,
        applicant_profile: ApplicantProfile,
        cover_letter_date: str,
    ) -> str:
        response = self._create_response(
            instructions=COVER_LETTER_SYSTEM_PROMPT,
            input=build_cover_letter_input(
                resume_text=resume_text,
                context_text=context_text,
                job_description=job_description,
                evaluation=evaluation,
                applicant_profile=applicant_profile,
                cover_letter_date=cover_letter_date,
            ),
            max_output_tokens=500,
        )
        refusal = extract_refusal_text(response)
        if refusal:
            raise ModelRefusalError(refusal)

        output_text = extract_output_text(response)
        if not output_text:
            raise OpenAIValidationError("OpenAI returned no cover letter output.")

        return normalize_cover_letter(
            output_text,
            applicant_profile=applicant_profile,
            cover_letter_date=cover_letter_date,
        )

    def _create_response(self, **kwargs: Any) -> Any:
        try:
            response = self.client.responses.create(
                model=self.requested_model,
                **kwargs,
            )
        except Exception as exc:
            fallback_model = self._fallback_model_for(exc)
            if not fallback_model:
                raise OpenAIValidationError(str(exc)) from exc

            try:
                response = self.client.responses.create(
                    model=fallback_model,
                    **kwargs,
                )
            except Exception as fallback_exc:
                raise OpenAIValidationError(
                    (
                        f"Fallback model `{fallback_model}` failed after "
                        f"`{self.requested_model}` was unavailable: {fallback_exc}"
                    )
                ) from fallback_exc
            self.active_model = fallback_model
            return response

        self.active_model = self.requested_model
        return response

    def _fallback_model_for(self, exc: Exception) -> str | None:
        if self.requested_model != DEFAULT_OPENAI_MODEL:
            return None
        if not self.fallback_model or self.fallback_model == self.requested_model:
            return None
        if not is_model_access_error(exc):
            return None
        return self.fallback_model

    def _validate_or_repair_evaluation(self, payload: Any) -> JobEvaluation:
        try:
            return JobEvaluation.model_validate(payload)
        except ValidationError as exc:
            normalized_payload = sanitize_job_evaluation_payload(payload)
            if normalized_payload != payload:
                try:
                    return JobEvaluation.model_validate(normalized_payload)
                except ValidationError:
                    pass

            repaired_payload = self._repair_evaluation_payload(
                payload=payload,
                validation_error=str(exc),
            )
            try:
                return JobEvaluation.model_validate(repaired_payload)
            except ValidationError as repaired_exc:
                raise OpenAIValidationError(
                    (
                        "OpenAI returned JSON that failed schema validation "
                        f"even after repair: {repaired_exc}"
                    )
                ) from repaired_exc

    def _repair_evaluation_payload(
        self,
        *,
        payload: Any,
        validation_error: str,
    ) -> Any:
        response = self._create_response(
            instructions=REPAIR_SYSTEM_PROMPT,
            input=build_job_fit_repair_input(
                invalid_payload=json.dumps(payload, indent=2, sort_keys=True),
                validation_error=validation_error,
            ),
            text={
                "format": {
                    "type": "json_schema",
                    "name": "job_fit_evaluation_repair",
                    "strict": True,
                    "schema": job_evaluation_openai_schema(),
                }
            },
            max_output_tokens=600,
        )
        refusal = extract_refusal_text(response)
        if refusal:
            raise ModelRefusalError(refusal)

        output_text = extract_output_text(response)
        if not output_text:
            raise OpenAIValidationError("OpenAI returned no repaired structured output.")

        try:
            return json.loads(output_text)
        except json.JSONDecodeError as exc:
            raise OpenAIValidationError("OpenAI returned invalid repaired JSON output.") from exc


def extract_output_text(response: Any) -> str | None:
    output_text = getattr(response, "output_text", None)
    if isinstance(output_text, str) and output_text.strip():
        return output_text.strip()

    parts: list[str] = []
    for item in extract_response_items(response):
        for content in item.get("content", []):
            if content.get("type") == "output_text" and content.get("text"):
                parts.append(content["text"])

    combined = "".join(parts).strip()
    return combined or None


def extract_refusal_text(response: Any) -> str | None:
    parts: list[str] = []
    for item in extract_response_items(response):
        for content in item.get("content", []):
            if content.get("type") == "refusal" and content.get("refusal"):
                parts.append(content["refusal"])

    refusal = " ".join(part.strip() for part in parts if part.strip()).strip()
    return refusal or None


def extract_response_items(response: Any) -> list[dict[str, Any]]:
    output = getattr(response, "output", [])
    normalized: list[dict[str, Any]] = []
    for item in output or []:
        if isinstance(item, dict):
            content = item.get("content", [])
            normalized.append({"content": [normalize_content(part) for part in content]})
            continue

        content = getattr(item, "content", []) or []
        normalized.append({"content": [normalize_content(part) for part in content]})

    return normalized


def normalize_content(content: Any) -> dict[str, Any]:
    if isinstance(content, dict):
        return content

    return {
        "type": getattr(content, "type", None),
        "text": getattr(content, "text", None),
        "refusal": getattr(content, "refusal", None),
    }


def is_model_access_error(exc: Exception) -> bool:
    status_code = getattr(exc, "status_code", None)
    body = getattr(exc, "body", None)
    message = ""

    if isinstance(body, dict):
        error = body.get("error", {})
        if isinstance(error, dict):
            message = str(error.get("message", ""))
            code = str(error.get("code", ""))
            if code == "model_not_found":
                return True

    message = message or str(exc)
    lowered = message.lower()
    if "does not have access to model" in lowered:
        return True
    if "model_not_found" in lowered:
        return True
    if status_code in {403, 404} and "model" in lowered:
        return True
    return False


def normalize_cover_letter(
    text: str,
    *,
    applicant_profile: ApplicantProfile,
    cover_letter_date: str,
) -> str:
    cleaned = text.replace("\r\n", "\n").strip()
    cleaned = cleaned.removeprefix("```").removesuffix("```").strip()
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    raw_paragraphs = [paragraph.strip() for paragraph in cleaned.split("\n\n") if paragraph.strip()]
    body_paragraphs = [
        paragraph
        for paragraph in raw_paragraphs
        if not is_cover_letter_shell_paragraph(
            paragraph,
            applicant_profile=applicant_profile,
            cover_letter_date=cover_letter_date,
        )
    ]
    if not body_paragraphs:
        body_paragraphs = [cleaned]
    body_paragraphs = trim_cover_letter_body_paragraphs(
        body_paragraphs[:3],
        max_words=MAX_COVER_LETTER_BODY_WORDS,
    )

    signer_name = applicant_profile.full_name or "Candidate"
    contact_header = build_cover_letter_contact_header(applicant_profile)
    letter_parts = []
    if contact_header:
        letter_parts.append(contact_header)
    letter_parts.extend(
        [
            cover_letter_date,
            "Dear Hiring Team,",
            *body_paragraphs,
            f"Best regards,\n{signer_name}",
        ]
    )
    return "\n\n".join(letter_parts)


def build_cover_letter_contact_header(applicant_profile: ApplicantProfile) -> str | None:
    lines = [
        applicant_profile.full_name,
        applicant_profile.email,
        applicant_profile.phone,
    ]
    cleaned = [line.strip() for line in lines if line and line.strip()]
    if not cleaned:
        return None
    return "\n".join(cleaned)


def trim_cover_letter_body_paragraphs(
    paragraphs: list[str],
    *,
    max_words: int,
) -> list[str]:
    trimmed = [normalize_spacing(paragraph) for paragraph in paragraphs if normalize_spacing(paragraph)]
    if word_count(" ".join(trimmed)) <= max_words:
        return trimmed

    for index in range(len(trimmed) - 1, -1, -1):
        other_words = word_count(" ".join(trimmed[:index] + trimmed[index + 1 :]))
        remaining = max_words - other_words
        if remaining <= 0:
            trimmed[index] = ""
            continue
        trimmed[index] = trim_paragraph_to_word_limit(trimmed[index], remaining)
        if word_count(" ".join(trimmed)) <= max_words:
            break

    compacted = [paragraph for paragraph in trimmed if paragraph]
    return compacted or paragraphs[:1]


def trim_paragraph_to_word_limit(paragraph: str, limit: int) -> str:
    normalized = normalize_spacing(paragraph)
    if word_count(normalized) <= limit:
        return normalized

    sentences = split_sentences(normalized)
    kept: list[str] = []
    for sentence in sentences:
        candidate = " ".join(kept + [sentence]).strip()
        if word_count(candidate) <= limit:
            kept.append(sentence)
            continue
        remaining = limit - word_count(" ".join(kept))
        if remaining > 0:
            fragment = trim_text_to_word_limit(sentence, remaining)
            if fragment:
                kept.append(fragment)
        break

    return " ".join(kept).strip() or trim_text_to_word_limit(normalized, limit)


def split_sentences(text: str) -> list[str]:
    matches = re.findall(r"[^.!?]+[.!?]?", text)
    return [match.strip() for match in matches if match.strip()]


def trim_text_to_word_limit(text: str, limit: int) -> str:
    words = normalize_spacing(text).split()
    if limit <= 0:
        return ""
    if len(words) <= limit:
        return " ".join(words)
    trimmed = " ".join(words[:limit]).rstrip(",;:")
    if trimmed and trimmed[-1] not in ".!?":
        trimmed += "..."
    return trimmed


def normalize_spacing(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def word_count(text: str) -> int:
    return len([word for word in normalize_spacing(text).split(" ") if word])


def is_cover_letter_shell_paragraph(
    paragraph: str,
    *,
    applicant_profile: ApplicantProfile,
    cover_letter_date: str,
) -> bool:
    normalized = paragraph.strip()
    lowered = normalized.lower()
    if not lowered:
        return True
    if lowered == cover_letter_date.lower():
        return True
    if lowered.startswith("dear "):
        return True
    if lowered.startswith(("best regards", "cheers", "sincerely")):
        return True
    if lowered == "candidate":
        return True
    if applicant_profile.full_name and lowered == applicant_profile.full_name.lower():
        return True
    if applicant_profile.email and applicant_profile.email.lower() in lowered:
        return True
    if applicant_profile.phone and applicant_profile.phone.lower() in lowered:
        return True
    return False


def sanitize_job_evaluation_payload(payload: Any) -> Any:
    if not isinstance(payload, dict):
        return payload

    sanitized = dict(payload)
    for field_name in ("top_strengths", "critical_gaps"):
        value = sanitized.get(field_name)
        if isinstance(value, list):
            cleaned_items = [
                str(item).strip()
                for item in value
                if isinstance(item, str) and item.strip()
            ]
            if len(cleaned_items) >= 3:
                sanitized[field_name] = cleaned_items[:3]

    feedback = sanitized.get("feedback")
    if isinstance(feedback, str):
        sanitized_feedback = trim_to_sentence_limit(feedback, limit=4)
        if sanitized_feedback:
            sanitized["feedback"] = sanitized_feedback

    for field_name in ("company", "role_title", "location", "source_url"):
        value = sanitized.get(field_name)
        if isinstance(value, str):
            normalized = value.strip()
            sanitized[field_name] = normalized or None

    return sanitized


def trim_to_sentence_limit(text: str, *, limit: int) -> str:
    stripped = text.strip()
    if not stripped:
        return stripped

    sentences = re.findall(r"[^.!?]+[.!?]?", stripped)
    cleaned_sentences = [sentence.strip() for sentence in sentences if sentence.strip()]
    if len(cleaned_sentences) <= limit:
        return stripped
    return " ".join(cleaned_sentences[:limit]).strip()
