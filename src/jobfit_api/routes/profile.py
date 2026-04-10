"""Profile CRUD routes."""

from __future__ import annotations

import base64

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from jobfit_api.database import get_db_session
from jobfit_api.dependencies import get_current_user
from jobfit_api.documents import UploadedDocumentInput
from jobfit_api.models import User
from jobfit_api.schemas import (
    ProfileCreateRequest,
    ProfileResponse,
    ProfileUpdateRequest,
    StoredProfileDocumentResponse,
    UploadedProfileDocumentRequest,
)
from jobfit_api.services import (
    ConflictError,
    NotFoundError,
    ProfileState,
    ValidationError,
    create_profile_state,
    get_profile_state,
    update_profile_state,
)

router = APIRouter(tags=["profile"])


@router.get("/profile", response_model=ProfileResponse)
def get_profile(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_db_session),
) -> ProfileResponse:
    try:
        state = get_profile_state(session, current_user.id)
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return build_profile_response(state)


@router.post("/profile", response_model=ProfileResponse, status_code=status.HTTP_201_CREATED)
def create_profile(
    payload: ProfileCreateRequest,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_db_session),
) -> ProfileResponse:
    try:
        state = create_profile_state(
            session,
            user_id=current_user.id,
            display_name=payload.display_name,
            location=payload.location,
            resume_text=payload.resume_text,
            context_text=payload.context_text,
            resume_upload=decode_upload(payload.resume_upload, field_name="resume_text"),
            context_upload=decode_upload(payload.context_upload, field_name="context_text"),
        )
        session.commit()
    except ConflictError as exc:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except ValidationError as exc:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    session.refresh(state.profile)
    return build_profile_response(state)


@router.patch("/profile", response_model=ProfileResponse)
def update_profile(
    payload: ProfileUpdateRequest,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_db_session),
) -> ProfileResponse:
    try:
        state = update_profile_state(
            session,
            user_id=current_user.id,
            display_name=payload.display_name,
            location=payload.location,
            resume_text=payload.resume_text,
            context_text=payload.context_text,
            resume_upload=decode_upload(payload.resume_upload, field_name="resume_text"),
            context_upload=decode_upload(payload.context_upload, field_name="context_text"),
        )
        session.commit()
    except NotFoundError as exc:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValidationError as exc:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    session.refresh(state.profile)
    return build_profile_response(state)


def build_profile_response(state: ProfileState) -> ProfileResponse:
    return ProfileResponse(
        id=state.profile.id,
        display_name=state.profile.display_name,
        location=state.profile.location,
        resume_text=state.resume_version.content,
        context_text=state.context_version.content,
        resume_version_id=state.resume_version.id,
        resume_version_number=state.resume_version.version_number,
        context_version_id=state.context_version.id,
        context_version_number=state.context_version.version_number,
        resume_source_file=build_stored_document_response(
            state.resume_version.source_file_name,
            state.resume_version.source_file_mime_type,
            state.resume_version.source_file_size_bytes,
        ),
        context_source_file=build_stored_document_response(
            state.context_version.source_file_name,
            state.context_version.source_file_mime_type,
            state.context_version.source_file_size_bytes,
        ),
        created_at=state.profile.created_at,
        updated_at=state.profile.updated_at,
    )


def decode_upload(payload: UploadedProfileDocumentRequest | None, *, field_name: str) -> UploadedDocumentInput | None:
    if payload is None:
        return None
    try:
        raw_bytes = base64.b64decode(payload.content_base64.encode("ascii"), validate=True)
    except (ValueError, UnicodeEncodeError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"{field_name} upload content is not valid base64.",
        ) from exc
    return UploadedDocumentInput(
        file_name=payload.file_name,
        content_type=payload.content_type,
        data=raw_bytes,
    )


def build_stored_document_response(
    file_name: str | None,
    content_type: str | None,
    size_bytes: int | None,
) -> StoredProfileDocumentResponse | None:
    if file_name is None or size_bytes is None:
        return None
    return StoredProfileDocumentResponse(
        file_name=file_name,
        content_type=content_type,
        size_bytes=size_bytes,
    )
