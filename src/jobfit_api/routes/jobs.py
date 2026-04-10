"""Jobs CRUD and status routes."""

from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from jobfit_api.database import get_db_session
from jobfit_api.dependencies import get_current_user
from jobfit_api.models import ApplicationStatusEvent, BackgroundTask, User
from jobfit_api.schemas import (
    BackgroundTaskSummaryResponse,
    CoverLetterSummaryResponse,
    EvaluationSummaryResponse,
    JobCreateRequest,
    JobDetailResponse,
    JobListItemResponse,
    JobStatusUpdateRequest,
    JobUpdateRequest,
    StatusEventResponse,
    TaskAcceptedResponse,
)
from jobfit_api.services import (
    JobState,
    NotFoundError,
    ValidationError,
    create_job_state,
    get_job_state,
    get_task_for_user,
    list_job_states_for_user,
    update_job,
    update_job_status,
)
from jobfit_api.task_processing import enqueue_cover_letter_regeneration_task, enqueue_score_task

router = APIRouter(tags=["jobs"])


@router.get("/jobs", response_model=list[JobListItemResponse])
def list_jobs(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_db_session),
) -> list[JobListItemResponse]:
    states = list_job_states_for_user(session, current_user.id)
    return [build_job_list_item(state) for state in states]


@router.post("/jobs", response_model=JobDetailResponse, status_code=status.HTTP_201_CREATED)
def create_job(
    payload: JobCreateRequest,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_db_session),
) -> JobDetailResponse:
    created_job_id: str | None = None
    try:
        state = create_job_state(
            session,
            user_id=current_user.id,
            profile_id=None,
            description=payload.description,
            source_url=payload.source_url,
            company=payload.company,
            role_title=payload.role_title,
            location=payload.location,
            current_status=payload.current_status,
        )
        created_job_id = state.job.id
        session.commit()
    except ValidationError as exc:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    state = get_job_state(session, user_id=current_user.id, job_id=created_job_id or state.job.id)
    return build_job_detail(state)


@router.get("/jobs/{job_id}", response_model=JobDetailResponse)
def get_job(
    job_id: str,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_db_session),
) -> JobDetailResponse:
    try:
        state = get_job_state(session, user_id=current_user.id, job_id=job_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return build_job_detail(state)


@router.patch("/jobs/{job_id}", response_model=JobDetailResponse)
def patch_job(
    job_id: str,
    payload: JobUpdateRequest,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_db_session),
) -> JobDetailResponse:
    try:
        update_job(
            session,
            user_id=current_user.id,
            job_id=job_id,
            description=payload.description,
            source_url=payload.source_url,
            company=payload.company,
            role_title=payload.role_title,
            location=payload.location,
        )
        session.commit()
    except NotFoundError as exc:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValidationError as exc:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    state = get_job_state(session, user_id=current_user.id, job_id=job_id)
    return build_job_detail(state)


@router.patch("/jobs/{job_id}/status", response_model=JobDetailResponse)
def patch_job_status(
    job_id: str,
    payload: JobStatusUpdateRequest,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_db_session),
) -> JobDetailResponse:
    try:
        update_job_status(
            session,
            user_id=current_user.id,
            job_id=job_id,
            status=payload.status,
        )
        session.commit()
    except NotFoundError as exc:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    state = get_job_state(session, user_id=current_user.id, job_id=job_id)
    return build_job_detail(state)


@router.post("/jobs/{job_id}/score", response_model=TaskAcceptedResponse, status_code=status.HTTP_202_ACCEPTED)
def score_job(
    job_id: str,
    request: Request,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_db_session),
) -> TaskAcceptedResponse:
    try:
        get_job_state(session, user_id=current_user.id, job_id=job_id)
        task_id = enqueue_score_task(
            app=request.app,
            background_tasks=background_tasks,
            user_id=current_user.id,
            job_id=job_id,
        )
        task = get_task_for_user(session, user_id=current_user.id, task_id=task_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return build_task_accepted_response(task)


@router.post(
    "/jobs/{job_id}/cover-letter/regenerate",
    response_model=TaskAcceptedResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def regenerate_cover_letter(
    job_id: str,
    request: Request,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_db_session),
) -> TaskAcceptedResponse:
    try:
        get_job_state(session, user_id=current_user.id, job_id=job_id)
        task_id = enqueue_cover_letter_regeneration_task(
            app=request.app,
            background_tasks=background_tasks,
            user_id=current_user.id,
            job_id=job_id,
        )
        task = get_task_for_user(session, user_id=current_user.id, task_id=task_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return build_task_accepted_response(task)


def build_job_list_item(state: JobState) -> JobListItemResponse:
    return JobListItemResponse(
        id=state.job.id,
        profile_id=state.job.profile_id,
        company=state.job.company,
        role_title=state.job.role_title,
        location=state.job.location,
        source_url=state.job.source_url,
        current_status=state.job.current_status,
        latest_evaluation=build_evaluation_summary(state.latest_evaluation),
        latest_cover_letter=build_cover_letter_summary(state.latest_cover_letter),
        latest_task=build_task_summary(state.latest_task),
        created_at=state.job.created_at,
        updated_at=state.job.updated_at,
    )


def build_job_detail(state: JobState) -> JobDetailResponse:
    return JobDetailResponse(
        id=state.job.id,
        profile_id=state.job.profile_id,
        company=state.job.company,
        role_title=state.job.role_title,
        location=state.job.location,
        source_url=state.job.source_url,
        description=state.job.description,
        current_status=state.job.current_status,
        created_at=state.job.created_at,
        updated_at=state.job.updated_at,
        status_history=[build_status_event(event) for event in state.status_history],
        latest_evaluation=build_evaluation_summary(state.latest_evaluation),
        latest_cover_letter=build_cover_letter_summary(state.latest_cover_letter),
        latest_task=build_task_summary(state.latest_task),
    )


def build_status_event(event: ApplicationStatusEvent) -> StatusEventResponse:
    return StatusEventResponse(
        id=event.id,
        previous_status=event.previous_status,
        next_status=event.next_status,
        created_at=event.created_at,
    )


def build_evaluation_summary(evaluation) -> EvaluationSummaryResponse | None:
    if evaluation is None:
        return None
    return EvaluationSummaryResponse(
        id=evaluation.id,
        score=evaluation.score,
        verdict=getattr(evaluation.verdict, "value", str(evaluation.verdict)),
        top_strengths=list(evaluation.top_strengths),
        critical_gaps=list(evaluation.critical_gaps),
        feedback=evaluation.feedback,
        model=evaluation.model,
        created_at=evaluation.created_at,
    )


def build_cover_letter_summary(cover_letter) -> CoverLetterSummaryResponse | None:
    if cover_letter is None:
        return None
    return CoverLetterSummaryResponse(
        id=cover_letter.id,
        evaluation_id=cover_letter.evaluation_id,
        content=cover_letter.content,
        created_at=cover_letter.created_at,
        updated_at=cover_letter.updated_at,
    )


def build_task_summary(task: BackgroundTask | None) -> BackgroundTaskSummaryResponse | None:
    if task is None:
        return None
    result_score = None
    result_verdict = None
    if isinstance(task.result, dict):
        score_value = task.result.get("score")
        result_score = int(score_value) if isinstance(score_value, int | float) else None
        verdict_value = task.result.get("verdict")
        result_verdict = str(verdict_value) if verdict_value is not None else None
    return BackgroundTaskSummaryResponse(
        id=task.id,
        task_type=task.task_type,
        status=task.status,
        error_message=task.error_message,
        result_score=result_score,
        result_verdict=result_verdict,
        attempt_count=task.attempt_count,
        max_attempts=task.max_attempts,
        can_retry=task_can_retry(task),
        created_at=task.created_at,
        updated_at=task.updated_at,
        last_attempt_at=task.last_attempt_at,
        next_retry_at=task.next_retry_at,
        completed_at=task.completed_at,
    )


def build_task_accepted_response(task: BackgroundTask) -> TaskAcceptedResponse:
    return TaskAcceptedResponse(
        task_id=task.id,
        status=task.status,
    )


def task_can_retry(task: BackgroundTask) -> bool:
    return task.status.value == "failed" and task.task_type.value in {"score_job", "generate_cover_letter"}
