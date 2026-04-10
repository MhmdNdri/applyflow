"""Internal cover letter library routes."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends

from jobfit_api.database import get_db_session
from jobfit_api.dependencies import get_current_user
from jobfit_api.models import CoverLetter, Evaluation, Job, User
from jobfit_api.schemas import CoverLetterListItemResponse

router = APIRouter(tags=["cover letters"])


@router.get("/cover-letters", response_model=list[CoverLetterListItemResponse])
def list_cover_letters(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_db_session),
) -> list[CoverLetterListItemResponse]:
    rows = session.execute(
        select(CoverLetter, Job, Evaluation)
        .join(Job, CoverLetter.job_id == Job.id)
        .outerjoin(Evaluation, CoverLetter.evaluation_id == Evaluation.id)
        .where(Job.user_id == current_user.id)
        .order_by(CoverLetter.updated_at.desc(), CoverLetter.created_at.desc())
    ).all()

    return [
        CoverLetterListItemResponse(
            id=cover_letter.id,
            job_id=job.id,
            evaluation_id=cover_letter.evaluation_id,
            company=job.company,
            role_title=job.role_title,
            current_status=job.current_status,
            score=evaluation.score if evaluation is not None else None,
            content=cover_letter.content,
            created_at=cover_letter.created_at,
            updated_at=cover_letter.updated_at,
        )
        for cover_letter, job, evaluation in rows
    ]
