"""Background task lookup and recovery routes."""

from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from jobfit_api.database import get_db_session
from jobfit_api.dependencies import get_current_user
from jobfit_api.models import BackgroundTaskType, User
from jobfit_api.queue import dispatch_task
from jobfit_api.schemas import BackgroundTaskResponse, TaskAcceptedResponse
from jobfit_api.services import NotFoundError, ValidationError, get_task_for_user, prepare_task_retry, serialize_json_field

router = APIRouter(tags=["tasks"])


@router.get("/tasks/{task_id}", response_model=BackgroundTaskResponse)
def get_task(
    task_id: str,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_db_session),
) -> BackgroundTaskResponse:
    try:
        task = get_task_for_user(session, user_id=current_user.id, task_id=task_id)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return BackgroundTaskResponse(
        id=task.id,
        user_id=task.user_id,
        job_id=task.job_id,
        task_type=task.task_type,
        status=task.status,
        provider_job_id=task.provider_job_id,
        payload=serialize_json_field(task.payload),
        result=serialize_json_field(task.result),
        error_message=task.error_message,
        attempt_count=task.attempt_count,
        max_attempts=task.max_attempts,
        can_retry=task_can_retry(task),
        created_at=task.created_at,
        updated_at=task.updated_at,
        last_attempt_at=task.last_attempt_at,
        next_retry_at=task.next_retry_at,
        completed_at=task.completed_at,
    )


@router.post("/tasks/{task_id}/retry", response_model=TaskAcceptedResponse, status_code=status.HTTP_202_ACCEPTED)
def retry_task(
    task_id: str,
    request: Request,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_db_session),
) -> TaskAcceptedResponse:
    try:
        task = prepare_task_retry(session, user_id=current_user.id, task_id=task_id)
        session.commit()
        dispatch_task(request.app, background_tasks, task.id)
        return TaskAcceptedResponse(task_id=task.id, status=task.status)
    except NotFoundError as exc:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValidationError as exc:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc


def task_can_retry(task) -> bool:
    return task.status.value == "failed" and task.task_type in {
        BackgroundTaskType.SCORE_JOB,
        BackgroundTaskType.GENERATE_COVER_LETTER,
    }
