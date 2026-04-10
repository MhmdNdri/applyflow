"""Background task creation and execution for scoring workflows."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import logging
from pathlib import Path
from typing import Callable, Protocol

from fastapi import BackgroundTasks
from fastapi import FastAPI

from jobfit_cli.config import AppConfig, ConfigurationError
from jobfit_core import (
    ApplicantProfile,
    JobApplicationService,
    OpenAIEvaluator,
    extract_applicant_profile,
    format_cover_letter_date,
)

from .models import (
    BackgroundTask,
    BackgroundTaskStatus,
    BackgroundTaskType,
    CoverLetter,
    Evaluation,
    EvaluationVerdict,
    Profile,
    User,
)
from .queue import dispatch_task, schedule_task_retry
from .settings import ApiSettings
from .services import (
    NotFoundError,
    ValidationError,
    create_background_task,
    get_job_state,
    get_latest_context_version,
    get_latest_evaluation,
    get_latest_resume_version,
)

logger = logging.getLogger(__name__)


class EvaluatorProtocol(Protocol):
    active_model: str

    def evaluate(self, resume_text: str, context_text: str, job_description: str): ...

    def generate_cover_letter(
        self,
        resume_text: str,
        context_text: str,
        job_description: str,
        evaluation,
        applicant_profile,
        cover_letter_date: str,
    ) -> str: ...


EvaluatorFactory = Callable[[Path], EvaluatorProtocol]


def default_evaluator_factory(root: Path) -> EvaluatorProtocol:
    config = AppConfig.from_env(root)
    if not config.openai_api_key:
        raise ConfigurationError("Missing OPENAI_API_KEY.")
    return OpenAIEvaluator(config.openai_api_key, config.openai_model)


def enqueue_score_task(
    *,
    app: FastAPI,
    background_tasks: BackgroundTasks,
    user_id: str,
    job_id: str,
) -> str:
    return enqueue_task(
        app=app,
        background_tasks=background_tasks,
        user_id=user_id,
        job_id=job_id,
        task_type=BackgroundTaskType.SCORE_JOB,
    )


def enqueue_cover_letter_regeneration_task(
    *,
    app: FastAPI,
    background_tasks: BackgroundTasks,
    user_id: str,
    job_id: str,
) -> str:
    return enqueue_task(
        app=app,
        background_tasks=background_tasks,
        user_id=user_id,
        job_id=job_id,
        task_type=BackgroundTaskType.GENERATE_COVER_LETTER,
    )


def enqueue_task(
    *,
    app: FastAPI,
    background_tasks: BackgroundTasks,
    user_id: str,
    job_id: str,
    task_type: BackgroundTaskType,
) -> str:
    with app.state.database.session() as session:
        state = get_job_state(session, user_id=user_id, job_id=job_id)
        task = create_background_task(
            session,
            user_id=user_id,
            job_id=state.job.id,
            task_type=task_type,
            payload={"job_id": state.job.id},
        )
        session.commit()
        task_id = task.id

    dispatch_task(app, background_tasks, task_id)
    return task_id


def run_task(api_settings: ApiSettings, evaluator_factory: EvaluatorFactory, task_id: str) -> None:
    config = AppConfig.from_env(api_settings.root)
    from .database import DatabaseManager
    from .models import ContextVersion, ResumeVersion

    database = DatabaseManager(api_settings)

    with database.session() as session:
        task = session.get(BackgroundTask, task_id)
        if task is None:
            return
        started_at = datetime.now(timezone.utc)
        task.status = BackgroundTaskStatus.RUNNING
        task.attempt_count += 1
        task.last_attempt_at = started_at
        task.next_retry_at = None
        task.completed_at = None
        session.commit()

    try:
        if task.task_type == BackgroundTaskType.SCORE_JOB:
            logger.info(
                json.dumps(
                    {
                        "event": "task.started",
                        "task_id": task_id,
                        "task_type": task.task_type.value,
                        "attempt": task.attempt_count,
                    }
                )
            )
            evaluator = evaluator_factory(api_settings.root)
            with database.session() as session:
                task = session.get(BackgroundTask, task_id)
                if task is None or task.job_id is None or task.user_id is None:
                    raise NotFoundError("Task job context not found.")
                job_state = get_job_state(session, user_id=task.user_id, job_id=task.job_id)
                if job_state.job.profile_id is None:
                    raise ValidationError("Job is not linked to a profile.")
                resume_version = get_latest_resume_version(session, job_state.job.profile_id)
                context_version = get_latest_context_version(session, job_state.job.profile_id)
                if resume_version is None or context_version is None:
                    raise NotFoundError("Profile version history is incomplete.")
                job_description = job_state.job.description
                resume_text = resume_version.content
                context_text = context_version.content
                applicant_profile = build_applicant_profile(
                    session,
                    user_id=task.user_id,
                    profile_id=job_state.job.profile_id,
                    resume_text=resume_text,
                )

            workflow = JobApplicationService(evaluator)
            artifacts = workflow.score_job(
                resume_text=resume_text,
                context_text=context_text,
                job_description=job_description,
                applicant_profile=applicant_profile,
            )

            with database.session() as session:
                task = session.get(BackgroundTask, task_id)
                if task is None or task.job_id is None:
                    raise NotFoundError("Task record disappeared during processing.")
                evaluation = Evaluation(
                    job_id=task.job_id,
                    resume_version_id=resume_version.id,
                    context_version_id=context_version.id,
                    score=artifacts.evaluation.score,
                    verdict=EvaluationVerdict(
                        getattr(artifacts.evaluation.verdict, "value", str(artifacts.evaluation.verdict))
                    ),
                    top_strengths=artifacts.evaluation.top_strengths,
                    critical_gaps=artifacts.evaluation.critical_gaps,
                    feedback=artifacts.evaluation.feedback,
                    model=artifacts.model_used or getattr(evaluator, "active_model", config.openai_model),
                    profile_hash=compute_profile_hash(resume_text, context_text),
                )
                session.add(evaluation)
                session.flush()
                cover_letter = CoverLetter(
                    job_id=task.job_id,
                    evaluation_id=evaluation.id,
                    content=artifacts.cover_letter,
                )
                session.add(cover_letter)
                session.flush()
                task.status = BackgroundTaskStatus.COMPLETED
                task.result = {
                    "evaluation_id": evaluation.id,
                    "cover_letter_id": cover_letter.id,
                    "score": evaluation.score,
                    "verdict": getattr(evaluation.verdict, "value", evaluation.verdict),
                }
                task.completed_at = datetime.now(timezone.utc)
                task.error_message = None
                task.next_retry_at = None
                session.commit()
                logger.info(
                    json.dumps(
                        {
                            "event": "task.completed",
                            "task_id": task_id,
                            "task_type": task.task_type.value,
                            "attempt": task.attempt_count,
                        }
                    )
                )
            return

        if task.task_type == BackgroundTaskType.GENERATE_COVER_LETTER:
            logger.info(
                json.dumps(
                    {
                        "event": "task.started",
                        "task_id": task_id,
                        "task_type": task.task_type.value,
                        "attempt": task.attempt_count,
                    }
                )
            )
            evaluator = evaluator_factory(api_settings.root)
            with database.session() as session:
                task = session.get(BackgroundTask, task_id)
                if task is None or task.job_id is None or task.user_id is None:
                    raise NotFoundError("Task job context not found.")
                job_state = get_job_state(session, user_id=task.user_id, job_id=task.job_id)
                latest_evaluation = get_latest_evaluation(session, task.job_id)
                if latest_evaluation is None:
                    raise ValidationError("No evaluation exists for this job yet.")

                resume_version = session.get(ResumeVersion, latest_evaluation.resume_version_id)
                context_version = session.get(ContextVersion, latest_evaluation.context_version_id)
                if resume_version is None or context_version is None:
                    raise NotFoundError("Evaluation profile snapshot is incomplete.")

                applicant_profile = build_applicant_profile(
                    session,
                    user_id=task.user_id,
                    profile_id=resume_version.profile_id,
                    resume_text=resume_version.content,
                )
                cover_letter_date = format_cover_letter_date(datetime.now().astimezone())
                cover_letter_text = evaluator.generate_cover_letter(
                    resume_text=resume_version.content,
                    context_text=context_version.content,
                    job_description=job_state.job.description,
                    evaluation=latest_evaluation,
                    applicant_profile=applicant_profile,
                    cover_letter_date=cover_letter_date,
                )

                cover_letter = CoverLetter(
                    job_id=task.job_id,
                    evaluation_id=latest_evaluation.id,
                    content=cover_letter_text,
                )
                session.add(cover_letter)
                session.flush()
                task.status = BackgroundTaskStatus.COMPLETED
                task.result = {
                    "evaluation_id": latest_evaluation.id,
                    "cover_letter_id": cover_letter.id,
                }
                task.completed_at = datetime.now(timezone.utc)
                task.error_message = None
                task.next_retry_at = None
                session.commit()
                logger.info(
                    json.dumps(
                        {
                            "event": "task.completed",
                            "task_id": task_id,
                            "task_type": task.task_type.value,
                            "attempt": task.attempt_count,
                        }
                    )
                )
            return

        raise ValidationError(f"Unsupported task type: {task.task_type}")
    except Exception as exc:
        with database.session() as session:
            task = session.get(BackgroundTask, task_id)
            if task is not None:
                task.error_message = str(exc)
                if should_schedule_retry(task, api_settings):
                    delay_ms = calculate_retry_delay_ms(task.attempt_count)
                    retry_at = datetime.now(timezone.utc).replace(microsecond=0)
                    retry_at = retry_at + seconds_to_timedelta(delay_ms / 1000)
                    task.status = BackgroundTaskStatus.QUEUED
                    task.next_retry_at = retry_at
                    task.completed_at = None
                    session.commit()
                    logger.warning(
                        json.dumps(
                            {
                                "event": "task.retry_scheduled",
                                "task_id": task_id,
                                "task_type": task.task_type.value,
                                "attempt": task.attempt_count,
                                "max_attempts": task.max_attempts,
                                "delay_ms": delay_ms,
                                "error_message": str(exc),
                            }
                        )
                    )
                    try:
                        schedule_task_retry(api_settings, task_id, delay_ms=delay_ms)
                    except Exception as retry_exc:
                        task = session.get(BackgroundTask, task_id)
                        if task is not None:
                            task.status = BackgroundTaskStatus.FAILED
                            task.next_retry_at = None
                            task.completed_at = datetime.now(timezone.utc)
                            task.error_message = f"{exc} (retry scheduling failed: {retry_exc})"
                            session.commit()
                        logger.exception(
                            json.dumps(
                                {
                                    "event": "task.retry_schedule_failed",
                                    "task_id": task_id,
                                    "task_type": getattr(task.task_type, "value", str(task.task_type)) if task else None,
                                }
                            )
                        )
                    return

                task.status = BackgroundTaskStatus.FAILED
                task.next_retry_at = None
                task.completed_at = datetime.now(timezone.utc)
                session.commit()
                logger.exception(
                    json.dumps(
                        {
                            "event": "task.failed",
                            "task_id": task_id,
                            "task_type": getattr(task.task_type, "value", str(task.task_type)),
                            "attempt": task.attempt_count,
                            "max_attempts": task.max_attempts,
                        }
                    )
                )
    finally:
        database.dispose()


def compute_profile_hash(resume_text: str, context_text: str) -> str:
    digest = hashlib.sha256()
    digest.update(resume_text.encode("utf-8"))
    digest.update(b"\n---\n")
    digest.update(context_text.encode("utf-8"))
    return digest.hexdigest()


def build_applicant_profile(
    session,
    *,
    user_id: str,
    profile_id: str | None,
    resume_text: str,
) -> ApplicantProfile:
    parsed = extract_applicant_profile(resume_text)
    profile = session.get(Profile, profile_id) if profile_id else None
    user = session.get(User, user_id)
    return ApplicantProfile(
        full_name=parsed.full_name or (profile.display_name if profile is not None else None),
        email=parsed.email or (user.email if user is not None else None),
        phone=parsed.phone,
    )


def calculate_retry_delay_ms(attempt_count: int) -> int:
    # 5s, 15s, 30s, 60s cap.
    schedule = {1: 5_000, 2: 15_000, 3: 30_000}
    return schedule.get(attempt_count, 60_000)


def should_schedule_retry(task: BackgroundTask, api_settings: ApiSettings) -> bool:
    if not api_settings.redis_url:
        return False
    if task.task_type not in {BackgroundTaskType.SCORE_JOB, BackgroundTaskType.GENERATE_COVER_LETTER}:
        return False
    return task.attempt_count < task.max_attempts


def seconds_to_timedelta(seconds: float):
    from datetime import timedelta

    return timedelta(seconds=seconds)
