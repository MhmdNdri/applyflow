"""Compatibility exports for shared prompt helpers."""

from jobfit_core.prompts import (
    ApplicantProfile,
    COVER_LETTER_SYSTEM_PROMPT,
    EVALUATION_SYSTEM_PROMPT,
    REPAIR_SYSTEM_PROMPT,
    build_cover_letter_input,
    build_job_fit_input,
    build_job_fit_repair_input,
    extract_applicant_profile,
    extract_full_name,
    infer_name_from_email,
    normalize_phone,
)

__all__ = [
    "ApplicantProfile",
    "COVER_LETTER_SYSTEM_PROMPT",
    "EVALUATION_SYSTEM_PROMPT",
    "REPAIR_SYSTEM_PROMPT",
    "build_cover_letter_input",
    "build_job_fit_input",
    "build_job_fit_repair_input",
    "extract_applicant_profile",
    "extract_full_name",
    "infer_name_from_email",
    "normalize_phone",
]
