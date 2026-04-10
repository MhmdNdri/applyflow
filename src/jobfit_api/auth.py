"""Authentication helpers for Clerk JWT verification."""

from __future__ import annotations

from dataclasses import dataclass
from functools import cached_property
from typing import Any


class AuthenticationError(RuntimeError):
    """Raised when authentication fails."""


@dataclass(slots=True)
class AuthContext:
    user_id: str
    session_id: str | None
    email: str | None
    raw_claims: dict[str, Any]


class TokenVerifier:
    def verify_token(self, token: str) -> AuthContext:
        raise NotImplementedError


class DisabledAuthTokenVerifier(TokenVerifier):
    def verify_token(self, token: str) -> AuthContext:
        raise AuthenticationError("Auth is disabled for this environment.")


class ClerkTokenVerifier(TokenVerifier):
    def __init__(
        self,
        *,
        jwks_url: str | None,
        issuer: str | None,
        audience: str | None = None,
        authorized_party: str | None = None,
    ) -> None:
        self.jwks_url = jwks_url
        self.issuer = issuer
        self.audience = audience
        self.authorized_party = authorized_party

    @cached_property
    def _jwk_client(self):
        if not self.jwks_url:
            raise AuthenticationError("CLERK_JWKS_URL is not configured.")
        try:
            import jwt
        except ImportError as exc:  # pragma: no cover
            raise AuthenticationError("PyJWT is not installed.") from exc
        return jwt.PyJWKClient(self.jwks_url)

    def verify_token(self, token: str) -> AuthContext:
        if not self.issuer:
            raise AuthenticationError("CLERK_ISSUER is not configured.")
        try:
            import jwt
        except ImportError as exc:  # pragma: no cover
            raise AuthenticationError("PyJWT is not installed.") from exc

        signing_key = self._jwk_client.get_signing_key_from_jwt(token)
        options = {"verify_aud": bool(self.audience)}
        claims = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            issuer=self.issuer,
            audience=self.audience if self.audience else None,
            options=options,
        )
        if self.authorized_party and claims.get("azp") != self.authorized_party:
            raise AuthenticationError("Token authorized party does not match.")

        user_id = claims.get("sub")
        if not user_id:
            raise AuthenticationError("Token is missing subject.")

        return AuthContext(
            user_id=user_id,
            session_id=claims.get("sid"),
            email=claims.get("email"),
            raw_claims=dict(claims),
        )


def build_token_verifier(settings) -> TokenVerifier:
    if not settings.auth_enabled:
        return DisabledAuthTokenVerifier()
    return ClerkTokenVerifier(
        jwks_url=settings.clerk_jwks_url,
        issuer=settings.clerk_issuer,
        audience=settings.clerk_audience,
        authorized_party=settings.clerk_authorized_party,
    )
