"""Command orchestration."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import sys
from typing import Callable, Protocol, TextIO

from .config import AppConfig, ConfigurationError
from .constants import DEFAULT_APPLICATION_STATUS
from .docs import GoogleDocsClient
from .models import JobEvaluation
from .openai_service import OpenAIEvaluator, OpenAIValidationError
from .prompts import ApplicantProfile, extract_applicant_profile
from .sheets import GoogleSheetsLogger, build_cover_letter_formula
from .storage import (
    archive_job_description,
    build_run_id,
    compute_profile_hash,
    ensure_data_directories,
    ensure_profile_templates,
    load_profile,
    relative_path,
    save_cover_letter,
    save_run_record,
)


class EvaluatorProtocol(Protocol):
    def validate_access(self) -> None: ...

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


class SheetsLoggerProtocol(Protocol):
    def validate_access(self) -> None: ...

    def append_row(self, row: list[str]) -> None: ...


class DocsClientProtocol(Protocol):
    def validate_access(self) -> None: ...

    def create_cover_letter_doc(self, *, title: str, content: str) -> str: ...


EvaluatorFactory = Callable[[AppConfig], EvaluatorProtocol]
SheetsFactory = Callable[[AppConfig], SheetsLoggerProtocol]
DocsFactory = Callable[[AppConfig], DocsClientProtocol]


def default_evaluator_factory(config: AppConfig) -> EvaluatorProtocol:
    if not config.openai_api_key:
        raise ConfigurationError("Missing OPENAI_API_KEY.")
    return OpenAIEvaluator(config.openai_api_key, config.openai_model)


def default_sheets_factory(config: AppConfig) -> SheetsLoggerProtocol:
    if not config.google_sheet_id:
        raise ConfigurationError("Missing GOOGLE_SHEET_ID.")
    if not config.google_oauth_client_file and not config.google_service_account_file:
        raise ConfigurationError(
            "Missing GOOGLE_OAUTH_CLIENT_FILE or GOOGLE_SERVICE_ACCOUNT_FILE."
        )
    return GoogleSheetsLogger(
        config.google_service_account_file,
        config.google_sheet_id,
        oauth_client_file=config.google_oauth_client_file,
        oauth_token_file=config.google_oauth_token_file,
    )


def default_docs_factory(config: AppConfig) -> DocsClientProtocol:
    if not config.google_oauth_client_file and not config.google_service_account_file:
        raise ConfigurationError(
            "Missing GOOGLE_OAUTH_CLIENT_FILE or GOOGLE_SERVICE_ACCOUNT_FILE."
        )
    return GoogleDocsClient(
        config.google_service_account_file,
        folder_id=config.google_drive_folder_id,
        oauth_client_file=config.google_oauth_client_file,
        oauth_token_file=config.google_oauth_token_file,
    )


def run_setup(
    *,
    root: Path | None = None,
    stdout: TextIO = sys.stdout,
    stderr: TextIO = sys.stderr,
    evaluator_factory: EvaluatorFactory = default_evaluator_factory,
    sheets_factory: SheetsFactory = default_sheets_factory,
    docs_factory: DocsFactory = default_docs_factory,
) -> int:
    config = AppConfig.from_env(root)
    ensure_data_directories(config.paths)
    created_files = ensure_profile_templates(config.paths)

    issues: list[str] = []

    print(f"Project root: {config.paths.root}", file=stdout)
    print(f".env loaded: {config.paths.env_file.exists()}", file=stdout)

    if created_files:
        print("Created profile templates:", file=stdout)
        for path in created_files:
            print(f"- {relative_path(config.paths.root, path)}", file=stdout)
    else:
        print("Profile templates already exist.", file=stdout)

    if config.missing_openai_vars():
        issues.extend(f"Missing {name}" for name in config.missing_openai_vars())
    else:
        try:
            evaluator = evaluator_factory(config)
            evaluator.validate_access()
            active_model = getattr(evaluator, "active_model", config.openai_model)
            if active_model != config.openai_model:
                print(
                    (
                        f"OpenAI validation: OK "
                        f"(requested {config.openai_model}, using fallback {active_model})"
                    ),
                    file=stdout,
                )
            else:
                print(f"OpenAI validation: OK ({active_model})", file=stdout)
        except Exception as exc:
            issues.append(f"OpenAI validation failed: {exc}")

    google_missing = config.missing_google_vars()
    if google_missing:
        issues.extend(f"Missing {name}" for name in google_missing)
    else:
        print(f"Google auth mode: {config.google_auth_mode_label()}", file=stdout)
        if config.google_oauth_client_file:
            print(
                (
                    "Google OAuth token path: "
                    f"{relative_path(config.paths.root, config.google_oauth_token_file)}"
                ),
                file=stdout,
            )
        try:
            docs_factory(config).validate_access()
            print("Google Docs validation: OK", file=stdout)
        except Exception as exc:
            issues.append(f"Google Docs validation failed: {exc}")

        try:
            sheets_factory(config).validate_access()
            print("Google Sheets validation: OK", file=stdout)
        except Exception as exc:
            issues.append(f"Google Sheets validation failed: {exc}")

    if issues:
        print("Setup issues:", file=stderr)
        for issue in issues:
            print(f"- {issue}", file=stderr)
        return 1

    print("Setup complete.", file=stdout)
    return 0


def run_score(
    *,
    root: Path | None = None,
    stdin: TextIO = sys.stdin,
    stdout: TextIO = sys.stdout,
    stderr: TextIO = sys.stderr,
    evaluator_factory: EvaluatorFactory = default_evaluator_factory,
    sheets_factory: SheetsFactory = default_sheets_factory,
    docs_factory: DocsFactory = default_docs_factory,
) -> int:
    config = AppConfig.from_env(root)
    ensure_data_directories(config.paths)

    try:
        resume_text, context_text = load_profile(config.paths)
    except ConfigurationError as exc:
        print(str(exc), file=stderr)
        return 1

    job_description = read_job_description(stdin=stdin, stdout=stdout).strip()
    if not job_description:
        print("No job description provided.", file=stderr)
        return 1

    if len(job_description) < 120:
        print(
            "Warning: job description is sparse; the score may be less reliable.",
            file=stderr,
        )

    try:
        emit_progress("Evaluating job fit...", stream=stderr)
        evaluator = evaluator_factory(config)
        evaluation = evaluator.evaluate(
            resume_text=resume_text,
            context_text=context_text,
            job_description=job_description,
        )
        applicant_profile = extract_applicant_profile(resume_text)
        cover_letter_date = format_cover_letter_date(datetime.now().astimezone())
        emit_progress("Generating cover letter...", stream=stderr)
        cover_letter = evaluator.generate_cover_letter(
            resume_text=resume_text,
            context_text=context_text,
            job_description=job_description,
            evaluation=evaluation,
            applicant_profile=applicant_profile,
            cover_letter_date=cover_letter_date,
        )
    except (ConfigurationError, OpenAIValidationError, ValueError) as exc:
        print(f"Scoring failed: {exc}", file=stderr)
        return 1

    run_id = build_run_id()
    timestamp = datetime.now(timezone.utc).isoformat()
    date_value = datetime.now().astimezone().date().isoformat()
    profile_hash = compute_profile_hash(resume_text, context_text)
    model_used = getattr(evaluator, "active_model", config.openai_model)
    archived_job_path = archive_job_description(
        config.paths,
        run_id,
        evaluation.company,
        evaluation.role_title,
        job_description,
    )
    cover_letter_path = save_cover_letter(
        config.paths,
        run_id,
        evaluation.company,
        evaluation.role_title,
        cover_letter,
    )

    run_record = {
        "run_id": run_id,
        "date": date_value,
        "timestamp": timestamp,
        "model": model_used,
        "profile_hash": profile_hash,
        "application_status": DEFAULT_APPLICATION_STATUS,
        "archived_job_path": relative_path(config.paths.root, archived_job_path),
        "cover_letter_path": relative_path(config.paths.root, cover_letter_path),
        "cover_letter_text": cover_letter,
        "cover_letter_doc_url": None,
        "evaluation": normalize_evaluation(evaluation),
        "doc_logging": {"status": "pending", "error": None},
        "sheet_logging": {"status": "pending", "error": None},
    }

    run_path = save_run_record(config.paths, run_id, run_record)

    exit_code = 0
    try:
        emit_progress("Creating Google Doc...", stream=stderr)
        document_url = docs_factory(config).create_cover_letter_doc(
            title=build_cover_letter_title(
                human_date=cover_letter_date,
                applicant_name=applicant_profile.full_name,
                company=evaluation.company,
                role_title=evaluation.role_title,
            ),
            content=cover_letter,
        )
        run_record["cover_letter_doc_url"] = document_url
        run_record["doc_logging"] = {"status": "created", "error": None}

        row = build_sheet_row(
            date_value=date_value,
            evaluation=evaluation,
            application_status=DEFAULT_APPLICATION_STATUS,
            cover_letter_doc_url=document_url,
            archived_job_path=relative_path(config.paths.root, archived_job_path),
            profile_hash=profile_hash,
            model=model_used,
        )
        emit_progress("Updating Google Sheet...", stream=stderr)
        sheets_factory(config).append_row(row)
        run_record["sheet_logging"] = {"status": "logged", "error": None}
    except Exception as exc:
        if run_record["cover_letter_doc_url"]:
            run_record["sheet_logging"] = {"status": "failed", "error": str(exc)}
            print(
                (
                    "Google Sheets logging failed. The evaluation and cover letter were saved locally, "
                    "and the Google Doc was created."
                ),
                file=stderr,
            )
            print(f"Sheets error: {exc}", file=stderr)
        else:
            run_record["doc_logging"] = {"status": "failed", "error": str(exc)}
            print(
                (
                    "Google Doc creation failed. The evaluation and cover letter were saved locally. "
                    "Fix Google Docs or Drive access and retry."
                ),
                file=stderr,
            )
            print(f"Docs error: {exc}", file=stderr)
        exit_code = 2
    finally:
        save_run_record(config.paths, run_id, run_record)

    print_score_report(
        evaluation=evaluation,
        cover_letter_path=relative_path(config.paths.root, cover_letter_path),
        cover_letter_doc_url=run_record["cover_letter_doc_url"],
        requested_model=config.openai_model,
        model_used=model_used,
        archived_job_path=relative_path(config.paths.root, archived_job_path),
        run_record_path=relative_path(config.paths.root, run_path),
        stdout=stdout,
    )
    return exit_code


def read_job_description(*, stdin: TextIO, stdout: TextIO) -> str:
    if stdin.isatty():
        print("Paste the job description, then finish with Ctrl-D:", file=stdout)
    return stdin.read()


def emit_progress(message: str, *, stream: TextIO) -> None:
    print(message, file=stream, flush=True)


def build_sheet_row(
    *,
    date_value: str,
    evaluation: JobEvaluation,
    application_status: str,
    cover_letter_doc_url: str,
    archived_job_path: str,
    profile_hash: str,
    model: str,
) -> list[str]:
    return [
        date_value,
        evaluation.company or "",
        evaluation.role_title or "",
        application_status,
        evaluation.location or "",
        evaluation.source_url or "",
        str(evaluation.score),
        verdict_value(evaluation),
        " | ".join(evaluation.top_strengths),
        " | ".join(evaluation.critical_gaps),
        evaluation.feedback,
        build_cover_letter_formula(cover_letter_doc_url),
        archived_job_path,
        profile_hash,
        model,
    ]


def normalize_evaluation(evaluation: JobEvaluation) -> dict[str, object]:
    dumped = evaluation.model_dump()
    verdict = dumped.get("verdict")
    dumped["verdict"] = getattr(verdict, "value", verdict)
    return dumped


def print_score_report(
    *,
    evaluation: JobEvaluation,
    cover_letter_path: str,
    cover_letter_doc_url: str | None,
    requested_model: str,
    model_used: str,
    archived_job_path: str,
    run_record_path: str,
    stdout: TextIO,
) -> None:
    print(f"Score: {evaluation.score}/100", file=stdout)
    if model_used != requested_model:
        print(
            f"Model used: {model_used} (fallback from {requested_model})",
            file=stdout,
        )
    else:
        print(f"Model used: {model_used}", file=stdout)
    print(f"Verdict: {verdict_value(evaluation).replace('_', ' ')}", file=stdout)
    if evaluation.company:
        print(f"Company: {evaluation.company}", file=stdout)
    if evaluation.role_title:
        print(f"Role: {evaluation.role_title}", file=stdout)
    if evaluation.location:
        print(f"Location: {evaluation.location}", file=stdout)
    if evaluation.source_url:
        print(f"Source URL: {evaluation.source_url}", file=stdout)
    print("Top strengths:", file=stdout)
    for item in evaluation.top_strengths:
        print(f"- {item}", file=stdout)
    print("Critical gaps:", file=stdout)
    for item in evaluation.critical_gaps:
        print(f"- {item}", file=stdout)
    print(f"Feedback: {evaluation.feedback}", file=stdout)
    print(f"Cover letter backup: {cover_letter_path}", file=stdout)
    if cover_letter_doc_url:
        print(f"Cover letter doc: {cover_letter_doc_url}", file=stdout)
    print(f"Archived job: {archived_job_path}", file=stdout)
    print(f"Run record: {run_record_path}", file=stdout)


def verdict_value(evaluation: JobEvaluation) -> str:
    return getattr(evaluation.verdict, "value", str(evaluation.verdict))


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
