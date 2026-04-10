"""Reusable job scoring workflows."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Callable, Protocol

from .models import JobEvaluation
from .prompts import ApplicantProfile, extract_applicant_profile


class EvaluatorProtocol(Protocol):
    def evaluate(
        self,
        resume_text: str,
        context_text: str,
        job_description: str,
    ) -> JobEvaluation: ...

    def generate_cover_letter(
        self,
        resume_text: str,
        context_text: str,
        job_description: str,
        evaluation: JobEvaluation,
        applicant_profile: ApplicantProfile,
        cover_letter_date: str,
    ) -> str: ...


@dataclass(slots=True)
class JobApplicationArtifacts:
    evaluation: JobEvaluation
    applicant_profile: ApplicantProfile
    cover_letter: str
    cover_letter_date: str
    model_used: str | None


class JobApplicationService:
    def __init__(self, evaluator: EvaluatorProtocol) -> None:
        self.evaluator = evaluator

    def score_job(
        self,
        *,
        resume_text: str,
        context_text: str,
        job_description: str,
        applicant_profile: ApplicantProfile | None = None,
        now: datetime | None = None,
        progress: Callable[[str], None] | None = None,
    ) -> JobApplicationArtifacts:
        if progress:
            progress("Evaluating job fit...")
        evaluation = self.evaluator.evaluate(
            resume_text=resume_text,
            context_text=context_text,
            job_description=job_description,
        )
        extracted_profile = extract_applicant_profile(resume_text)
        applicant_profile = merge_applicant_profiles(
            primary=extracted_profile,
            fallback=applicant_profile,
        )
        cover_letter_date = format_cover_letter_date(
            (now or datetime.now().astimezone())
        )
        if progress:
            progress("Generating cover letter...")
        cover_letter = self.evaluator.generate_cover_letter(
            resume_text=resume_text,
            context_text=context_text,
            job_description=job_description,
            evaluation=evaluation,
            applicant_profile=applicant_profile,
            cover_letter_date=cover_letter_date,
        )
        return JobApplicationArtifacts(
            evaluation=evaluation,
            applicant_profile=applicant_profile,
            cover_letter=cover_letter,
            cover_letter_date=cover_letter_date,
            model_used=getattr(self.evaluator, "active_model", None),
        )


def merge_applicant_profiles(
    *,
    primary: ApplicantProfile,
    fallback: ApplicantProfile | None,
) -> ApplicantProfile:
    if fallback is None:
        return primary
    return ApplicantProfile(
        full_name=primary.full_name or fallback.full_name,
        email=primary.email or fallback.email,
        phone=primary.phone or fallback.phone,
    )


def verdict_value(evaluation: JobEvaluation) -> str:
    return getattr(evaluation.verdict, "value", str(evaluation.verdict))


def normalize_evaluation(evaluation: JobEvaluation) -> dict[str, object]:
    dumped = evaluation.model_dump()
    verdict = dumped.get("verdict")
    dumped["verdict"] = getattr(verdict, "value", verdict)
    return dumped


def build_cover_letter_title(
    *,
    human_date: str,
    applicant_name: str | None,
    company: str | None,
    role_title: str | None,
) -> str:
    name_value = applicant_name or "Candidate"
    company_value = company or "Unknown Company"
    role_value = role_title or "Role"
    return f"{human_date} - {name_value} - {role_value} - {company_value} Cover Letter"


def format_cover_letter_date(current_dt: datetime) -> str:
    return f"{current_dt.day} {current_dt.strftime('%B %Y')}"
