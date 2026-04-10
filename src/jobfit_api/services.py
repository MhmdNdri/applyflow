"""Database-backed domain services for Phase 3 API routes."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .documents import ExtractedDocument, UploadedDocumentInput, extract_uploaded_document
from .auth import AuthContext
from .models import (
    ApplicationStatus,
    ApplicationStatusEvent,
    BackgroundTask,
    BackgroundTaskStatus,
    BackgroundTaskType,
    ContextVersion,
    CoverLetter,
    Evaluation,
    Job,
    Profile,
    ResumeVersion,
    User,
)


class ServiceError(RuntimeError):
    """Base class for API service failures."""


class NotFoundError(ServiceError):
    """Raised when a requested record does not exist."""


class ConflictError(ServiceError):
    """Raised when a create request conflicts with existing state."""


class ValidationError(ServiceError):
    """Raised when provided input is invalid."""


@dataclass(slots=True)
class ProfileState:
    profile: Profile
    resume_version: ResumeVersion
    context_version: ContextVersion


@dataclass(slots=True)
class JobState:
    job: Job
    status_history: list[ApplicationStatusEvent]
    latest_evaluation: Evaluation | None = None
    latest_cover_letter: CoverLetter | None = None
    latest_task: BackgroundTask | None = None


@dataclass(slots=True)
class PreparedProfileDocument:
    text: str
    file_name: str | None = None
    file_mime_type: str | None = None
    file_size_bytes: int | None = None
    file_bytes: bytes | None = None


def ensure_user(session: Session, auth_context: AuthContext) -> User:
    user = session.scalar(
        select(User).where(User.clerk_user_id == auth_context.user_id)
    )
    if user is None:
        user = User(
            clerk_user_id=auth_context.user_id,
            email=normalize_optional_text(auth_context.email),
        )
        session.add(user)
        session.flush()
        return user

    normalized_email = normalize_optional_text(auth_context.email)
    if user.email != normalized_email:
        user.email = normalized_email
        session.flush()
    return user


def get_profile_state(session: Session, user_id: str) -> ProfileState:
    profile = session.scalar(select(Profile).where(Profile.user_id == user_id))
    if profile is None:
        raise NotFoundError("Profile not found.")

    resume_version = get_latest_resume_version(session, profile.id)
    context_version = get_latest_context_version(session, profile.id)
    if resume_version is None or context_version is None:
        raise NotFoundError("Profile version history is incomplete.")

    return ProfileState(
        profile=profile,
        resume_version=resume_version,
        context_version=context_version,
    )


def create_profile_state(
    session: Session,
    *,
    user_id: str,
    display_name: str | None,
    location: str | None,
    resume_text: str | None,
    context_text: str | None,
    resume_upload: UploadedDocumentInput | None = None,
    context_upload: UploadedDocumentInput | None = None,
) -> ProfileState:
    existing = session.scalar(select(Profile).where(Profile.user_id == user_id))
    if existing is not None:
        raise ConflictError("Profile already exists.")

    prepared_resume = prepare_profile_document(
        text=resume_text,
        upload=resume_upload,
        field_name="resume_text",
    )
    prepared_context = prepare_profile_document(
        text=context_text,
        upload=context_upload,
        field_name="context_text",
    )

    profile = Profile(
        user_id=user_id,
        display_name=normalize_optional_text(display_name),
        location=normalize_optional_text(location),
    )
    session.add(profile)
    session.flush()

    resume_version = ResumeVersion(
        profile_id=profile.id,
        version_number=1,
        content=prepared_resume.text,
        source_file_name=prepared_resume.file_name,
        source_file_mime_type=prepared_resume.file_mime_type,
        source_file_size_bytes=prepared_resume.file_size_bytes,
        source_file_bytes=prepared_resume.file_bytes,
    )
    context_version = ContextVersion(
        profile_id=profile.id,
        version_number=1,
        content=prepared_context.text,
        source_file_name=prepared_context.file_name,
        source_file_mime_type=prepared_context.file_mime_type,
        source_file_size_bytes=prepared_context.file_size_bytes,
        source_file_bytes=prepared_context.file_bytes,
    )
    session.add_all([resume_version, context_version])
    session.flush()

    return ProfileState(
        profile=profile,
        resume_version=resume_version,
        context_version=context_version,
    )


def update_profile_state(
    session: Session,
    *,
    user_id: str,
    display_name: str | None = None,
    location: str | None = None,
    resume_text: str | None = None,
    context_text: str | None = None,
    resume_upload: UploadedDocumentInput | None = None,
    context_upload: UploadedDocumentInput | None = None,
) -> ProfileState:
    state = get_profile_state(session, user_id)
    changed = False

    if display_name is not None:
        normalized_name = normalize_optional_text(display_name)
        if state.profile.display_name != normalized_name:
            state.profile.display_name = normalized_name
            changed = True

    if location is not None:
        normalized_location = normalize_optional_text(location)
        if state.profile.location != normalized_location:
            state.profile.location = normalized_location
            changed = True

    if resume_text is not None or resume_upload is not None:
        prepared_resume = prepare_profile_document(
            text=resume_text,
            upload=resume_upload,
            field_name="resume_text",
            existing=state.resume_version,
        )
        if resume_version_has_changed(state.resume_version, prepared_resume):
            state.resume_version = ResumeVersion(
                profile_id=state.profile.id,
                version_number=next_resume_version_number(session, state.profile.id),
                content=prepared_resume.text,
                source_file_name=prepared_resume.file_name,
                source_file_mime_type=prepared_resume.file_mime_type,
                source_file_size_bytes=prepared_resume.file_size_bytes,
                source_file_bytes=prepared_resume.file_bytes,
            )
            session.add(state.resume_version)
            changed = True

    if context_text is not None or context_upload is not None:
        prepared_context = prepare_profile_document(
            text=context_text,
            upload=context_upload,
            field_name="context_text",
            existing=state.context_version,
        )
        if context_version_has_changed(state.context_version, prepared_context):
            state.context_version = ContextVersion(
                profile_id=state.profile.id,
                version_number=next_context_version_number(session, state.profile.id),
                content=prepared_context.text,
                source_file_name=prepared_context.file_name,
                source_file_mime_type=prepared_context.file_mime_type,
                source_file_size_bytes=prepared_context.file_size_bytes,
                source_file_bytes=prepared_context.file_bytes,
            )
            session.add(state.context_version)
            changed = True

    if not changed:
        raise ValidationError("No profile changes were provided.")

    session.flush()
    return state


def list_jobs_for_user(session: Session, user_id: str) -> list[Job]:
    return list(
        session.scalars(
            select(Job)
            .where(Job.user_id == user_id)
            .order_by(Job.created_at.desc())
        )
    )


def list_job_states_for_user(session: Session, user_id: str) -> list[JobState]:
    jobs = list_jobs_for_user(session, user_id)
    states: list[JobState] = []
    for job in jobs:
        states.append(
            enrich_job_state(
                session,
                JobState(
                    job=job,
                    status_history=[],
                ),
            )
        )
    return states


def get_job_state(session: Session, *, user_id: str, job_id: str) -> JobState:
    job = session.scalar(
        select(Job).where(Job.id == job_id, Job.user_id == user_id)
    )
    if job is None:
        raise NotFoundError("Job not found.")

    status_history = list(
        session.scalars(
            select(ApplicationStatusEvent)
            .where(ApplicationStatusEvent.job_id == job.id)
            .order_by(ApplicationStatusEvent.created_at.asc(), ApplicationStatusEvent.id.asc())
        )
    )

    return enrich_job_state(session, JobState(job=job, status_history=status_history))


def create_job_state(
    session: Session,
    *,
    user_id: str,
    profile_id: str | None,
    description: str,
    source_url: str | None,
    company: str | None,
    role_title: str | None,
    location: str | None,
    current_status: ApplicationStatus,
) -> JobState:
    resolved_profile_id = profile_id
    if resolved_profile_id is None:
        profile = session.scalar(select(Profile).where(Profile.user_id == user_id))
        resolved_profile_id = profile.id if profile is not None else None

    job = Job(
        user_id=user_id,
        profile_id=resolved_profile_id,
        description=require_text(description, field_name="description"),
        source_url=normalize_optional_text(source_url),
        company=normalize_optional_text(company),
        role_title=normalize_optional_text(role_title),
        location=normalize_optional_text(location),
        current_status=current_status,
    )
    session.add(job)
    session.flush()

    initial_event = ApplicationStatusEvent(
        job_id=job.id,
        previous_status=None,
        next_status=current_status,
    )
    session.add(initial_event)
    session.flush()

    return enrich_job_state(session, JobState(job=job, status_history=[initial_event]))


def update_job(
    session: Session,
    *,
    user_id: str,
    job_id: str,
    description: str | None = None,
    source_url: str | None = None,
    company: str | None = None,
    role_title: str | None = None,
    location: str | None = None,
) -> JobState:
    state = get_job_state(session, user_id=user_id, job_id=job_id)
    changed = False

    if description is not None:
        normalized_description = require_text(description, field_name="description")
        if state.job.description != normalized_description:
            state.job.description = normalized_description
            changed = True

    for field_name, value in (
        ("source_url", source_url),
        ("company", company),
        ("role_title", role_title),
        ("location", location),
    ):
        if value is None:
            continue
        normalized_value = normalize_optional_text(value)
        if getattr(state.job, field_name) != normalized_value:
            setattr(state.job, field_name, normalized_value)
            changed = True

    if not changed:
        raise ValidationError("No job changes were provided.")

    session.flush()
    return enrich_job_state(session, state)


def update_job_status(
    session: Session,
    *,
    user_id: str,
    job_id: str,
    status: ApplicationStatus,
) -> JobState:
    state = get_job_state(session, user_id=user_id, job_id=job_id)
    if state.job.current_status == status:
        return state

    event = ApplicationStatusEvent(
        job_id=state.job.id,
        previous_status=state.job.current_status,
        next_status=status,
    )
    state.job.current_status = status
    session.add(event)
    session.flush()
    state.status_history.append(event)
    return enrich_job_state(session, state)


def get_task_for_user(session: Session, *, user_id: str, task_id: str) -> BackgroundTask:
    task = session.scalar(
        select(BackgroundTask).where(
            BackgroundTask.id == task_id,
            BackgroundTask.user_id == user_id,
        )
    )
    if task is None:
        raise NotFoundError("Task not found.")
    return task


def create_background_task(
    session: Session,
    *,
    user_id: str,
    job_id: str,
    task_type,
    payload: dict[str, Any] | None = None,
) -> BackgroundTask:
    task = BackgroundTask(
        user_id=user_id,
        job_id=job_id,
        task_type=task_type,
        payload=payload,
        max_attempts=default_max_attempts(task_type),
    )
    session.add(task)
    session.flush()
    return task


def prepare_task_retry(
    session: Session,
    *,
    user_id: str,
    task_id: str,
) -> BackgroundTask:
    task = get_task_for_user(session, user_id=user_id, task_id=task_id)
    if task.task_type not in {BackgroundTaskType.SCORE_JOB, BackgroundTaskType.GENERATE_COVER_LETTER}:
        raise ValidationError("This task type cannot be retried from the workspace.")
    if task.status != BackgroundTaskStatus.FAILED:
        raise ValidationError("Only failed tasks can be retried.")
    if task.job_id is None:
        raise ValidationError("This task is missing its job context.")

    if task.attempt_count >= task.max_attempts:
        task.max_attempts = task.attempt_count + 1

    task.status = BackgroundTaskStatus.QUEUED
    task.error_message = None
    task.completed_at = None
    task.next_retry_at = None
    task.result = None
    session.flush()
    return task


def get_latest_evaluation(session: Session, job_id: str) -> Evaluation | None:
    return session.scalar(
        select(Evaluation)
        .where(Evaluation.job_id == job_id)
        .order_by(Evaluation.created_at.desc(), Evaluation.id.desc())
        .limit(1)
    )


def get_latest_cover_letter(session: Session, job_id: str) -> CoverLetter | None:
    return session.scalar(
        select(CoverLetter)
        .where(CoverLetter.job_id == job_id)
        .order_by(CoverLetter.created_at.desc(), CoverLetter.id.desc())
        .limit(1)
    )


def get_latest_background_task(session: Session, job_id: str) -> BackgroundTask | None:
    return session.scalar(
        select(BackgroundTask)
        .where(BackgroundTask.job_id == job_id)
        .order_by(BackgroundTask.updated_at.desc(), BackgroundTask.created_at.desc(), BackgroundTask.id.desc())
        .limit(1)
    )


def get_latest_resume_version(session: Session, profile_id: str) -> ResumeVersion | None:
    return session.scalar(
        select(ResumeVersion)
        .where(ResumeVersion.profile_id == profile_id)
        .order_by(ResumeVersion.version_number.desc())
        .limit(1)
    )


def get_latest_context_version(session: Session, profile_id: str) -> ContextVersion | None:
    return session.scalar(
        select(ContextVersion)
        .where(ContextVersion.profile_id == profile_id)
        .order_by(ContextVersion.version_number.desc())
        .limit(1)
    )


def next_resume_version_number(session: Session, profile_id: str) -> int:
    max_version = session.scalar(
        select(func.max(ResumeVersion.version_number)).where(
            ResumeVersion.profile_id == profile_id
        )
    )
    return int(max_version or 0) + 1


def next_context_version_number(session: Session, profile_id: str) -> int:
    max_version = session.scalar(
        select(func.max(ContextVersion.version_number)).where(
            ContextVersion.profile_id == profile_id
        )
    )
    return int(max_version or 0) + 1


def enrich_job_state(session: Session, state: JobState) -> JobState:
    state.latest_evaluation = get_latest_evaluation(session, state.job.id)
    state.latest_cover_letter = get_latest_cover_letter(session, state.job.id)
    state.latest_task = get_latest_background_task(session, state.job.id)
    return state


def require_text(value: str, *, field_name: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValidationError(f"{field_name} must not be empty.")
    return normalized


def normalize_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


def serialize_json_field(value: dict[str, Any] | None) -> dict[str, Any] | None:
    return value if value is not None else None


def default_max_attempts(task_type: BackgroundTaskType) -> int:
    if task_type == BackgroundTaskType.SCORE_JOB:
        return 3
    if task_type == BackgroundTaskType.GENERATE_COVER_LETTER:
        return 2
    return 1


def prepare_profile_document(
    *,
    text: str | None,
    upload: UploadedDocumentInput | None,
    field_name: str,
    existing: ResumeVersion | ContextVersion | None = None,
) -> PreparedProfileDocument:
    normalized_text = normalize_optional_text(text)
    extracted: ExtractedDocument | None = None
    if upload is not None:
        try:
            extracted = extract_uploaded_document(upload, field_name=field_name)
        except ValueError as exc:
            raise ValidationError(str(exc)) from exc

    if normalized_text is None and extracted is None and existing is None:
        raise ValidationError(f"{field_name} must not be empty.")

    resolved_text = normalized_text or (extracted.text if extracted is not None else None)
    if resolved_text is None and existing is not None:
        resolved_text = existing.content

    if resolved_text is None:
        raise ValidationError(f"{field_name} must not be empty.")

    if extracted is not None:
        return PreparedProfileDocument(
            text=resolved_text.strip(),
            file_name=extracted.file_name,
            file_mime_type=extracted.content_type,
            file_size_bytes=extracted.size_bytes,
            file_bytes=extracted.raw_bytes,
        )

    if existing is not None:
        return PreparedProfileDocument(
            text=resolved_text.strip(),
            file_name=existing.source_file_name,
            file_mime_type=existing.source_file_mime_type,
            file_size_bytes=existing.source_file_size_bytes,
            file_bytes=existing.source_file_bytes,
        )

    return PreparedProfileDocument(text=resolved_text.strip())


def resume_version_has_changed(version: ResumeVersion, prepared: PreparedProfileDocument) -> bool:
    return version_has_changed(
        current_text=version.content,
        current_file_name=version.source_file_name,
        current_file_mime_type=version.source_file_mime_type,
        current_file_size_bytes=version.source_file_size_bytes,
        current_file_bytes=version.source_file_bytes,
        prepared=prepared,
    )


def context_version_has_changed(version: ContextVersion, prepared: PreparedProfileDocument) -> bool:
    return version_has_changed(
        current_text=version.content,
        current_file_name=version.source_file_name,
        current_file_mime_type=version.source_file_mime_type,
        current_file_size_bytes=version.source_file_size_bytes,
        current_file_bytes=version.source_file_bytes,
        prepared=prepared,
    )


def version_has_changed(
    *,
    current_text: str,
    current_file_name: str | None,
    current_file_mime_type: str | None,
    current_file_size_bytes: int | None,
    current_file_bytes: bytes | None,
    prepared: PreparedProfileDocument,
) -> bool:
    return any(
        (
            current_text != prepared.text,
            current_file_name != prepared.file_name,
            current_file_mime_type != prepared.file_mime_type,
            current_file_size_bytes != prepared.file_size_bytes,
            current_file_bytes != prepared.file_bytes,
        )
    )
