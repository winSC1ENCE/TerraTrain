"""App user authentication: login, refresh, logout, password change.

Sessions are httpOnly cookies (access + refresh JWTs) plus a non-httpOnly
double-submit CSRF cookie; see ``api/deps.py`` for how requests are
authenticated and CSRF-checked. There is no self-registration — accounts
are created by an admin (see the admin router).

Strava OAuth has been removed; intervals.icu (per-user API key, configured
in User Settings) is now the sole external integration.
"""

import secrets
import uuid

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from terratrain.api.deps import get_current_active_user, get_session
from terratrain.config import get_settings
from terratrain.db.models.user import User
from terratrain.rate_limit import limiter
from terratrain.schemas.auth import ChangePasswordRequest, LoginRequest, UserResponse
from terratrain.services.auth_service import (
    InvalidTokenError,
    TokenType,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)

logger = structlog.get_logger()
router = APIRouter()


def _set_session_cookies(response: Response, *, access_token: str, refresh_token: str) -> None:
    settings = get_settings()
    response.set_cookie(
        settings.access_token_cookie_name,
        access_token,
        max_age=settings.access_token_expire_minutes * 60,
        httponly=True,
        secure=settings.secure_cookies,
        samesite="lax",
        path="/",
    )
    response.set_cookie(
        settings.refresh_token_cookie_name,
        refresh_token,
        max_age=settings.refresh_token_expire_days * 86400,
        httponly=True,
        secure=settings.secure_cookies,
        samesite="lax",
        path="/",
    )
    # CSRF cookie must be readable by frontend JS to echo back as a header
    # (double-submit pattern) — deliberately NOT httpOnly.
    response.set_cookie(
        settings.csrf_cookie_name,
        secrets.token_urlsafe(32),
        max_age=settings.refresh_token_expire_days * 86400,
        httponly=False,
        secure=settings.secure_cookies,
        samesite="lax",
        path="/",
    )


def _clear_session_cookies(response: Response) -> None:
    settings = get_settings()
    for name in (
        settings.access_token_cookie_name,
        settings.refresh_token_cookie_name,
        settings.csrf_cookie_name,
    ):
        response.delete_cookie(name, path="/")


@router.post("/login", response_model=UserResponse)
@limiter.limit("5/minute")
async def login(
    request: Request,
    body: LoginRequest,
    response: Response,
    session: AsyncSession = Depends(get_session),
) -> User:
    result = await session.execute(select(User).where(User.email == body.email.lower()))
    user = result.scalar_one_or_none()
    if user is None or not verify_password(body.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid email or password"
        )
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="account is disabled")

    access_token = create_access_token(user_id=user.id, role=user.role)
    refresh_token = create_refresh_token(user_id=user.id, role=user.role)
    _set_session_cookies(response, access_token=access_token, refresh_token=refresh_token)
    logger.info("auth.login", user_id=str(user.id))
    return user


@router.post("/refresh", response_model=UserResponse)
async def refresh(
    request: Request,
    response: Response,
    session: AsyncSession = Depends(get_session),
) -> User:
    settings = get_settings()
    token = request.cookies.get(settings.refresh_token_cookie_name)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="no refresh token")

    try:
        payload = decode_token(token, expected_type=TokenType.REFRESH)
    except InvalidTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid or expired refresh token"
        ) from exc

    user = await session.get(User, uuid.UUID(payload["sub"]))
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="user not found or disabled"
        )

    # Rotate both tokens on refresh.
    access_token = create_access_token(user_id=user.id, role=user.role)
    refresh_token = create_refresh_token(user_id=user.id, role=user.role)
    _set_session_cookies(response, access_token=access_token, refresh_token=refresh_token)
    return user


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(response: Response) -> None:
    _clear_session_cookies(response)


@router.get("/me", response_model=UserResponse)
async def me(user: User = Depends(get_current_active_user)) -> User:
    return user


@router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT)
async def change_password(
    body: ChangePasswordRequest,
    user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_session),
) -> None:
    if not verify_password(body.current_password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="current password is incorrect"
        )

    user.hashed_password = hash_password(body.new_password)
    user.must_change_password = False
    await session.commit()
    logger.info("auth.change_password", user_id=str(user.id))
