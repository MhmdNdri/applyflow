"""SQLAlchemy models for the fullstack foundation."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
import uuid

from sqlalchemy import JSON, DateTime, Enum as SqlEnum, ForeignKey, Integer, LargeBinary, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def generate_uuid() -> str:
    return str(uuid.uuid4())


def enum_values(enum_cls: type[Enum]) -> list[str]:
    return [str(member.value) for member in enum_cls]


def db_enum(enum_cls: type[Enum], *, name: str) -> SqlEnum:
    return SqlEnum(
        enum_cls,
        name=name,
        values_callable=enum_values,
        validate_strings=True,
    )


class Base(DeclarativeBase):
    """Shared declarative base."""


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )


class ApplicationStatus(str, Enum):
    WISHLIST = "wishlist"
    APPLIED = "applied"
    WAITING = "waiting"
    RECRUITER_SCREEN = "recruiter screen"
    INTERVIEW_SCHEDULED = "interview scheduled"
    INTERVIEWING = "interviewing"
    FINAL_ROUND = "final round"
    OFFER = "offer"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"


class EvaluationVerdict(str, Enum):
    STRONG_FIT = "strong_fit"
    POSSIBLE_FIT = "possible_fit"
    WEAK_FIT = "weak_fit"
    NOT_FIT = "not_fit"


class BackgroundTaskStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class BackgroundTaskType(str, Enum):
    SCORE_JOB = "score_job"
    GENERATE_COVER_LETTER = "generate_cover_letter"


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    clerk_user_id: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    email: Mapped[str | None] = mapped_column(String(320), nullable=True)


class Profile(Base, TimestampMixin):
    __tablename__ = "profiles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    display_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)


class ResumeVersion(Base):
    __tablename__ = "resume_versions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    profile_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    source_file_name: Mapped[str | None] = mapped_column(String(512), nullable=True)
    source_file_mime_type: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source_file_size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source_file_bytes: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    __table_args__ = (
        UniqueConstraint("profile_id", "version_number", name="uq_resume_versions_profile_version"),
    )


class ContextVersion(Base):
    __tablename__ = "context_versions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    profile_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    source_file_name: Mapped[str | None] = mapped_column(String(512), nullable=True)
    source_file_mime_type: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source_file_size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source_file_bytes: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    __table_args__ = (
        UniqueConstraint("profile_id", "version_number", name="uq_context_versions_profile_version"),
    )


class Job(Base, TimestampMixin):
    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    profile_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("profiles.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    company: Mapped[str | None] = mapped_column(String(255), nullable=True)
    role_title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    current_status: Mapped[ApplicationStatus] = mapped_column(
        db_enum(ApplicationStatus, name="application_status"),
        nullable=False,
        default=ApplicationStatus.WAITING,
    )


class Evaluation(Base):
    __tablename__ = "evaluations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    job_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    resume_version_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("resume_versions.id", ondelete="SET NULL"),
        nullable=True,
    )
    context_version_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("context_versions.id", ondelete="SET NULL"),
        nullable=True,
    )
    score: Mapped[int] = mapped_column(Integer, nullable=False)
    verdict: Mapped[EvaluationVerdict] = mapped_column(
        db_enum(EvaluationVerdict, name="evaluation_verdict"),
        nullable=False,
    )
    top_strengths: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    critical_gaps: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    feedback: Mapped[str] = mapped_column(Text, nullable=False)
    model: Mapped[str] = mapped_column(String(255), nullable=False)
    profile_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class CoverLetter(Base):
    __tablename__ = "cover_letters"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    job_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    evaluation_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("evaluations.id", ondelete="SET NULL"),
        nullable=True,
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)


class ApplicationStatusEvent(Base):
    __tablename__ = "application_status_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    job_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    previous_status: Mapped[ApplicationStatus | None] = mapped_column(
        db_enum(ApplicationStatus, name="application_status"),
        nullable=True,
    )
    next_status: Mapped[ApplicationStatus] = mapped_column(
        db_enum(ApplicationStatus, name="application_status"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class BackgroundTask(Base):
    __tablename__ = "background_tasks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    user_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    job_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("jobs.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    task_type: Mapped[BackgroundTaskType] = mapped_column(
        db_enum(BackgroundTaskType, name="background_task_type"),
        nullable=False,
    )
    status: Mapped[BackgroundTaskStatus] = mapped_column(
        db_enum(BackgroundTaskStatus, name="background_task_status"),
        nullable=False,
        default=BackgroundTaskStatus.QUEUED,
    )
    provider_job_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    payload: Mapped[dict[str, object] | None] = mapped_column(JSON, nullable=True)
    result: Mapped[dict[str, object] | None] = mapped_column(JSON, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    last_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    next_retry_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
