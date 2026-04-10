"""Shared FastAPI dependencies."""

from __future__ import annotations

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from .auth import AuthContext, AuthenticationError, TokenVerifier
from .database import get_db_session
from .models import User
from .services import ensure_user

bearer_scheme = HTTPBearer(auto_error=False)


def require_auth(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> AuthContext:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token.",
        )

    verifier: TokenVerifier = request.app.state.token_verifier
    try:
        return verifier.verify_token(credentials.credentials)
    except AuthenticationError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        ) from exc


def get_current_user(
    auth_context: AuthContext = Depends(require_auth),
    session: Session = Depends(get_db_session),
) -> User:
    user = ensure_user(session, auth_context)
    session.flush()
    session.commit()
    session.refresh(user)
    return user
