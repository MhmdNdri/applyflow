"""Project constants."""

from __future__ import annotations

DEFAULT_OPENAI_MODEL = "gpt-5.4-mini"
OPENAI_MODEL_FALLBACK = "gpt-4o-mini"

LEGACY_SHEET_HEADERS = [
    "timestamp",
    "company",
    "role_title",
    "location",
    "source_url",
    "score",
    "verdict",
    "top_strengths_summary",
    "critical_gaps_summary",
    "feedback",
    "archived_job_path",
    "profile_hash",
    "model",
]

INTERMEDIATE_SHEET_HEADERS = [
    "date",
    "company",
    "role_title",
    "location",
    "source_url",
    "score",
    "verdict",
    "top_strengths_summary",
    "critical_gaps_summary",
    "feedback",
    "cover_letter_doc_url",
    "archived_job_path",
    "profile_hash",
    "model",
]

SHEET_HEADERS = [
    "date",
    "company",
    "role_title",
    "application_status",
    "location",
    "source_url",
    "score",
    "verdict",
    "top_strengths_summary",
    "critical_gaps_summary",
    "feedback",
    "cover_letter_doc_url",
    "archived_job_path",
    "profile_hash",
    "model",
]

APPLICATION_STATUS_OPTIONS = [
    "wishlist",
    "applied",
    "waiting",
    "recruiter screen",
    "interview scheduled",
    "interviewing",
    "final round",
    "offer",
    "accepted",
    "rejected",
    "withdrawn",
]

DEFAULT_APPLICATION_STATUS = "waiting"

COVER_LETTER_LINK_LABEL = "Open cover letter"

RESUME_TEMPLATE = """# Resume

Add your latest resume here.

Recommended sections:
- Full name
- Email
- Phone
- Headline
- Experience
- Skills
- Education
- Certifications
- Highlights with metrics
"""

CONTEXT_TEMPLATE = """# Honest Context

Add the honest context the evaluator should remember across the full workflow.

Suggested topics:
- Roles you truly want
- Roles you do not want
- Industries you know well
- Strengths you can prove
- Skills you are still learning
- Work authorization or location constraints
- Salary expectations or deal-breakers
"""
