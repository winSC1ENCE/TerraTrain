import uuid
from collections.abc import AsyncGenerator

import structlog
from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from terratrain.config import get_settings
from terratrain.db.engine import get_db_session
from terratrain.db.models.athlete import Athlete
from terratrain.db.models.user import User
from terratrain.services.auth_service import InvalidTokenError, TokenType, decode_token

logger = structlog.get_logger()

# Requests that mutate state and therefore need the double-submit CSRF check
# (GET/HEAD/OPTIONS are safe and exempt).
_UNSAFE_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})


async def get_session(
    session: AsyncSession = Depends(get_db_session),
) -> AsyncGenerator[AsyncSession, None]:
    yield session


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail)


def _verify_csrf(request: Request) -> None:
    """Double-submit CSRF check for cookie-authenticated mutating requests.

    The access/refresh cookies are httpOnly, so a cross-site request can't
    read them to forge a matching header — only a same-origin page (which
    can read the non-httpOnly CSRF cookie) can supply the matching header.
    """
    settings = get_settings()
    cookie_value = request.cookies.get(settings.csrf_cookie_name)
    header_value = request.headers.get(settings.csrf_header_name)
    if not cookie_value or not header_value or cookie_value != header_value:
        raise _unauthorized("missing or invalid CSRF token")


async def get_current_user(
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> User:
    settings = get_settings()
    token = request.cookies.get(settings.access_token_cookie_name)
    if not token:
        raise _unauthorized("not authenticated")

    try:
        payload = decode_token(token, expected_type=TokenType.ACCESS)
    except InvalidTokenError as exc:
        raise _unauthorized("invalid or expired session") from exc

    if request.method in _UNSAFE_METHODS:
        _verify_csrf(request)

    try:
        user_id = uuid.UUID(payload["sub"])
    except (KeyError, ValueError) as exc:
        raise _unauthorized("invalid session subject") from exc

    user = await session.get(User, user_id)
    if user is None:
        raise _unauthorized("user not found")
    return user


async def get_current_active_user(user: User = Depends(get_current_user)) -> User:
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="account is disabled")
    return user


async def require_admin(user: User = Depends(get_current_active_user)) -> User:
    if user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="admin role required")
    return user


async def get_current_athlete(
    user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_session),
) -> Athlete:
    """The authenticated user's own athlete profile.

    Every athlete-scoped router depends on this instead of accepting an
    ``athlete_id`` from the client, so no request can act on another
    user's data by supplying a foreign id.
    """
    result = await session.execute(select(Athlete).where(Athlete.user_id == user.id))
    athlete = result.scalar_one_or_none()
    if athlete is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="no athlete profile for this user"
        )
    return athlete
