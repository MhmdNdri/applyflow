"""Prompt construction shared across interfaces."""

from __future__ import annotations

from dataclasses import dataclass
import re

from .models import JobEvaluation

EVALUATION_SYSTEM_PROMPT = """You are an honest and strict resume-to-job evaluator.

Evaluate the candidate against the job description using only evidence that appears in the supplied resume and context.

Rules:
- Return a score from 0 to 100.
- Be strict and realistic, not flattering.
- Penalize missing must-have requirements heavily.
- Reward proven experience and concrete evidence over vague potential.
- Do not invent missing metadata. Use null for unknown company, title, location, or source_url.
- Return exactly 3 top_strengths and exactly 3 critical_gaps.
- Keep feedback direct, concise, and within 4 sentences.
"""

COVER_LETTER_SYSTEM_PROMPT = """You write concise, human, warm-professional cover letters.

Rules:
- Write exactly 3 short body paragraphs.
- Keep the tone warm, polished, and natural.
- Be slightly creative, but still professional and believable.
- Keep the full letter comfortably within one page once the app adds the date, greeting, and sign-off.
- Target roughly 150 to 210 words across the 3 body paragraphs.
- Ground every claim in the supplied resume and honest context.
- Tailor the letter to the role and company when known.
- Prefer specific, credible evidence from the resume over generic enthusiasm.
- If the fit has gaps, frame them honestly and positively without apologizing too much.
- Do not invent achievements, numbers, tools, or domain expertise.
- Do not include the date, greeting, sign-off, applicant name, email, phone, postal address block, placeholders, bullet points, or markdown.
- Return only the 3 body paragraphs.
"""

REPAIR_SYSTEM_PROMPT = """You repair JSON so it matches a required schema exactly.

Rules:
- Return valid JSON only.
- Keep the original intent and evidence.
- Do not invent unsupported achievements or metadata.
- Ensure the result matches the target schema exactly.
"""


def build_job_fit_input(resume_text: str, context_text: str, job_description: str) -> str:
    return "\n\n".join(
        [
            "Candidate Resume:",
            resume_text.strip(),
            "Candidate Honest Context:",
            context_text.strip(),
            "Job Description:",
            job_description.strip(),
            (
                "Return strict JSON that matches the schema exactly. "
                "The score should reflect actual fit for this exact role, not general career potential."
            ),
        ]
    )


@dataclass(slots=True)
class ApplicantProfile:
    full_name: str | None
    email: str | None
    phone: str | None


def build_cover_letter_input(
    resume_text: str,
    context_text: str,
    job_description: str,
    evaluation: JobEvaluation,
    applicant_profile: ApplicantProfile,
    cover_letter_date: str,
) -> str:
    return "\n\n".join(
        [
            "Candidate Resume:",
            resume_text.strip(),
            "Candidate Honest Context:",
            context_text.strip(),
            "Job Description:",
            job_description.strip(),
            "Fit Summary:",
            (
                f"Score: {evaluation.score}/100\n"
                f"Role Title: {evaluation.role_title or 'Unknown'}\n"
                f"Company: {evaluation.company or 'Unknown'}\n"
                f"Top Strengths: {'; '.join(evaluation.top_strengths)}\n"
                f"Critical Gaps: {'; '.join(evaluation.critical_gaps)}\n"
                f"Feedback: {evaluation.feedback}"
            ),
            "Applicant Details:",
            (
                f"Full Name: {applicant_profile.full_name or 'Unknown'}\n"
                f"Email: {applicant_profile.email or 'Unknown'}\n"
                f"Phone: {applicant_profile.phone or 'Unknown'}\n"
                f"Application Date: {cover_letter_date}"
            ),
            "Final Letter Shell Added By The App:",
            (
                f"{applicant_profile.full_name or 'Candidate'}\n"
                f"{applicant_profile.email or ''}\n"
                f"{applicant_profile.phone or ''}\n\n"
                f"{cover_letter_date}\n\n"
                "Dear Hiring Team,\n\n"
                "[Paragraph 1]\n\n"
                "[Paragraph 2]\n\n"
                "[Paragraph 3]\n\n"
                f"Best regards,\n{applicant_profile.full_name or 'Unknown'}"
            ),
            (
                "Write only the 3 body paragraphs that should sit between the greeting and the sign-off. "
                "Do not repeat the date, greeting, or sign-off. "
                "Target roughly 150 to 210 words across the body and keep it concise enough to fit on one page."
            ),
        ]
    )


def build_job_fit_repair_input(
    *,
    invalid_payload: str,
    validation_error: str,
) -> str:
    return "\n\n".join(
        [
            "The previous JSON output did not pass validation.",
            f"Validation error: {validation_error}",
            "Invalid JSON payload:",
            invalid_payload.strip(),
            (
                "Repair the JSON so it exactly matches the required schema. "
                "Keep the same scoring intent, trim extras if needed, and use null for unknown optional fields."
            ),
        ]
    )


def extract_applicant_profile(resume_text: str) -> ApplicantProfile:
    email_match = re.search(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", resume_text, re.IGNORECASE)
    phone_match = re.search(
        r"(?:(?:\+?\d{1,3}[\s().-]*)?(?:\(?\d{2,4}\)?[\s().-]*){2,4}\d{2,4})",
        resume_text,
    )
    full_name = extract_full_name(resume_text)
    email = email_match.group(0).strip() if email_match else None
    if not full_name and email:
        full_name = infer_name_from_email(email)
    phone = normalize_phone(phone_match.group(0)) if phone_match else None
    return ApplicantProfile(
        full_name=full_name,
        email=email,
        phone=phone,
    )


def extract_full_name(resume_text: str) -> str | None:
    lines = [line.strip() for line in resume_text.replace("\r\n", "\n").splitlines()]
    for line in lines:
        if not line:
            continue
        candidate = line.lstrip("#").strip()
        candidate = re.sub(r"^(name|full name)\s*:\s*", "", candidate, flags=re.IGNORECASE)
        candidate = candidate.strip("*_ ").strip()
        if "@" in candidate or any(char.isdigit() for char in candidate):
            continue
        words = [word for word in re.split(r"\s+", candidate) if word]
        if 2 <= len(words) <= 5 and all(re.fullmatch(r"[A-Za-z][A-Za-z'.-]*", word) for word in words):
            return " ".join(words)
    return None


def normalize_phone(value: str) -> str | None:
    cleaned = re.sub(r"\s+", " ", value).strip(" ,;|")
    digit_count = len(re.sub(r"\D", "", cleaned))
    if digit_count < 7:
        return None
    return cleaned


def infer_name_from_email(email: str) -> str | None:
    local_part = email.split("@", maxsplit=1)[0]
    chunks = [chunk for chunk in re.split(r"[^A-Za-z]+", local_part) if len(chunk) > 1]
    if len(chunks) >= 2:
        return " ".join(word.capitalize() for word in chunks[-2:])
    if chunks:
        return chunks[0].capitalize()
    return None
