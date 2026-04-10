"""Pydantic API schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

from .models import ApplicationStatus, BackgroundTaskStatus, BackgroundTaskType


class ServiceHealth(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["ok", "degraded", "not_configured"]
    detail: str


class HealthResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["ok", "degraded"]
    environment: str
    services: dict[str, ServiceHealth]


class AuthMeResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_id: str
    session_id: str | None
    email: str | None


class UploadedProfileDocumentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    file_name: str
    content_type: str | None = None
    content_base64: str


class StoredProfileDocumentResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    file_name: str
    content_type: str | None
    size_bytes: int


class ProfileCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    display_name: str | None = None
    location: str | None = None
    resume_text: str | None = None
    context_text: str | None = None
    resume_upload: UploadedProfileDocumentRequest | None = None
    context_upload: UploadedProfileDocumentRequest | None = None


class ProfileUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    display_name: str | None = None
    location: str | None = None
    resume_text: str | None = None
    context_text: str | None = None
    resume_upload: UploadedProfileDocumentRequest | None = None
    context_upload: UploadedProfileDocumentRequest | None = None


class ProfileResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    display_name: str | None
    location: str | None
    resume_text: str
    context_text: str
    resume_version_id: str
    resume_version_number: int
    context_version_id: str
    context_version_number: int
    resume_source_file: StoredProfileDocumentResponse | None = None
    context_source_file: StoredProfileDocumentResponse | None = None
    created_at: datetime
    updated_at: datetime


class StatusEventResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    previous_status: ApplicationStatus | None
    next_status: ApplicationStatus
    created_at: datetime


class JobCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    description: str
    source_url: str | None = None
    company: str | None = None
    role_title: str | None = None
    location: str | None = None
    current_status: ApplicationStatus = ApplicationStatus.WAITING


class JobUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    description: str | None = None
    source_url: str | None = None
    company: str | None = None
    role_title: str | None = None
    location: str | None = None


class JobStatusUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: ApplicationStatus


class JobListItemResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    profile_id: str | None
    company: str | None
    role_title: str | None
    location: str | None
    source_url: str | None
    current_status: ApplicationStatus
    latest_evaluation: "EvaluationSummaryResponse | None" = None
    latest_cover_letter: "CoverLetterSummaryResponse | None" = None
    latest_task: "BackgroundTaskSummaryResponse | None" = None
    created_at: datetime
    updated_at: datetime


class EvaluationSummaryResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    score: int
    verdict: str
    top_strengths: list[str]
    critical_gaps: list[str]
    feedback: str
    model: str
    created_at: datetime


class BackgroundTaskSummaryResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    task_type: BackgroundTaskType
    status: BackgroundTaskStatus
    error_message: str | None
    result_score: int | None = None
    result_verdict: str | None = None
    attempt_count: int
    max_attempts: int
    can_retry: bool
    created_at: datetime
    updated_at: datetime
    last_attempt_at: datetime | None
    next_retry_at: datetime | None
    completed_at: datetime | None


class CoverLetterSummaryResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    evaluation_id: str | None
    content: str
    created_at: datetime
    updated_at: datetime


class CoverLetterListItemResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    job_id: str
    evaluation_id: str | None
    company: str | None
    role_title: str | None
    current_status: ApplicationStatus
    score: int | None = None
    content: str
    created_at: datetime
    updated_at: datetime


class JobDetailResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    profile_id: str | None
    company: str | None
    role_title: str | None
    location: str | None
    source_url: str | None
    description: str
    current_status: ApplicationStatus
    created_at: datetime
    updated_at: datetime
    status_history: list[StatusEventResponse]
    latest_evaluation: EvaluationSummaryResponse | None = None
    latest_cover_letter: CoverLetterSummaryResponse | None = None
    latest_task: BackgroundTaskSummaryResponse | None = None


class BackgroundTaskResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    user_id: str | None
    job_id: str | None
    task_type: BackgroundTaskType
    status: BackgroundTaskStatus
    provider_job_id: str | None
    payload: dict[str, Any] | None
    result: dict[str, Any] | None
    error_message: str | None
    attempt_count: int
    max_attempts: int
    can_retry: bool
    created_at: datetime
    updated_at: datetime
    last_attempt_at: datetime | None
    next_retry_at: datetime | None
    completed_at: datetime | None


class TaskAcceptedResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    task_id: str
    status: BackgroundTaskStatus
