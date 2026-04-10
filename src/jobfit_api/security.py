"""Small signing and encryption helpers for API integrations."""

from __future__ import annotations

import base64
from datetime import UTC, datetime
import hashlib
import hmac
import json
from typing import Any

from cryptography.fernet import Fernet, InvalidToken


class SignatureError(RuntimeError):
    """Raised when a signed payload is invalid."""


def encrypt_text(secret: str, value: str) -> str:
    token = _fernet(secret).encrypt(value.encode("utf-8"))
    return token.decode("utf-8")


def decrypt_text(secret: str, value: str) -> str:
    try:
        decrypted = _fernet(secret).decrypt(value.encode("utf-8"))
    except InvalidToken as exc:  # pragma: no cover - depends on persisted invalid data
        raise SignatureError("Stored token could not be decrypted.") from exc
    return decrypted.decode("utf-8")


def sign_payload(payload: dict[str, Any], secret: str) -> str:
    encoded_payload = _encode_json(payload)
    signature = hmac.new(
        secret.encode("utf-8"),
        encoded_payload.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    encoded_signature = base64.urlsafe_b64encode(signature).decode("utf-8").rstrip("=")
    return f"{encoded_payload}.{encoded_signature}"


def verify_signed_payload(
    token: str,
    secret: str,
    *,
    max_age_seconds: int | None = None,
) -> dict[str, Any]:
    try:
        encoded_payload, encoded_signature = token.split(".", maxsplit=1)
    except ValueError as exc:
        raise SignatureError("Malformed state token.") from exc

    expected_signature = base64.urlsafe_b64encode(
        hmac.new(
            secret.encode("utf-8"),
            encoded_payload.encode("utf-8"),
            hashlib.sha256,
        ).digest()
    ).decode("utf-8").rstrip("=")
    if not hmac.compare_digest(encoded_signature, expected_signature):
        raise SignatureError("State token signature is invalid.")

    try:
        payload = json.loads(_decode_base64(encoded_payload))
    except json.JSONDecodeError as exc:
        raise SignatureError("State token payload is invalid.") from exc

    if max_age_seconds is not None:
        issued_at = payload.get("iat")
        if not isinstance(issued_at, int | float):
            raise SignatureError("State token is missing a valid timestamp.")
        age = datetime.now(UTC).timestamp() - float(issued_at)
        if age < 0 or age > max_age_seconds:
            raise SignatureError("State token has expired.")

    return payload


def _encode_json(payload: dict[str, Any]) -> str:
    raw = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("utf-8").rstrip("=")


def _decode_base64(value: str) -> str:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(f"{value}{padding}".encode("utf-8")).decode("utf-8")


def _fernet(secret: str) -> Fernet:
    digest = hashlib.sha256(secret.encode("utf-8")).digest()
    return Fernet(base64.urlsafe_b64encode(digest))
