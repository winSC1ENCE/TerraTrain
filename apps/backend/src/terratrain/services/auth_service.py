"""Password hashing and JWT access/refresh token handling.

Used by the ``auth`` router (login/refresh/logout) and by
``api/deps.py`` (``get_current_user``) to authenticate requests.
Access tokens are short-lived and carry the user id + role; refresh
tokens are long-lived and only used to mint a new access token.
"""

import uuid
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import Any

import bcrypt
import structlog
from jose import JWTError, jwt

from terratrain.config import get_settings

logger = structlog.get_logger()

# bcrypt truncates/errors past 72 bytes; hash inputs are pre-validated (short
# passwords) but we guard here too so a long input degrades safely rather
# than raising deep inside a login request.
_BCRYPT_MAX_BYTES = 72


class TokenType(StrEnum):
    ACCESS = "access"
    REFRESH = "refresh"


class InvalidTokenError(Exception):
    """Raised when a JWT is missing, expired, malformed, or the wrong type."""


def hash_password(password: str) -> str:
    truncated = password.encode("utf-8")[:_BCRYPT_MAX_BYTES]
    return bcrypt.hashpw(truncated, bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, hashed_password: str) -> bool:
    truncated = password.encode("utf-8")[:_BCRYPT_MAX_BYTES]
    try:
        return bcrypt.checkpw(truncated, hashed_password.encode("utf-8"))
    except ValueError:
        # Malformed/foreign hash format (e.g. corrupted row) — never authenticate.
        return False


def _create_token(
    *, user_id: uuid.UUID, role: str, token_type: TokenType, expires_delta: timedelta
) -> str:
    settings = get_settings()
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "role": role,
        "type": token_type.value,
        "iat": now,
        "exp": now + expires_delta,
    }
    encoded: str = jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)
    return encoded


def create_access_token(*, user_id: uuid.UUID, role: str) -> str:
    settings = get_settings()
    return _create_token(
        user_id=user_id,
        role=role,
        token_type=TokenType.ACCESS,
        expires_delta=timedelta(minutes=settings.access_token_expire_minutes),
    )


def create_refresh_token(*, user_id: uuid.UUID, role: str) -> str:
    settings = get_settings()
    return _create_token(
        user_id=user_id,
        role=role,
        token_type=TokenType.REFRESH,
        expires_delta=timedelta(days=settings.refresh_token_expire_days),
    )


def decode_token(token: str, *, expected_type: TokenType) -> dict[str, Any]:
    """Decode and validate a JWT, raising ``InvalidTokenError`` on any problem."""
    settings = get_settings()
    try:
        payload: dict[str, Any] = jwt.decode(
            token, settings.secret_key, algorithms=[settings.jwt_algorithm]
        )
    except JWTError as exc:
        raise InvalidTokenError("token is invalid or expired") from exc

    if payload.get("type") != expected_type.value:
        raise InvalidTokenError(f"expected a {expected_type.value} token")

    return payload
