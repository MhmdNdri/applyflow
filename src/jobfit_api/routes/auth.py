"""Auth and session endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from jobfit_api.dependencies import require_auth
from jobfit_api.schemas import AuthMeResponse

router = APIRouter(tags=["auth"])


@router.get("/auth/me", response_model=AuthMeResponse)
def get_me(auth_context = Depends(require_auth)) -> AuthMeResponse:
    return AuthMeResponse(
        user_id=auth_context.user_id,
        session_id=auth_context.session_id,
        email=auth_context.email,
    )
