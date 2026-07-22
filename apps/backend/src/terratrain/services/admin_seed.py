"""Seed the first admin account on application startup.

Runs once, at process start: if no admin user exists yet, create one with a
random one-time password and require it to be changed on first login. This
is the only supported way to obtain admin credentials — there is no open
self-registration (accounts are admin-invited).
"""

import secrets

import structlog
from sqlalchemy import func, select

from terratrain.config import get_settings
from terratrain.db.engine import get_session_factory
from terratrain.db.models.user import User
from terratrain.services.auth_service import hash_password

logger = structlog.get_logger()


async def seed_initial_admin() -> None:
    settings = get_settings()
    session_factory = get_session_factory()

    async with session_factory() as session:
        existing_admin_count = await session.scalar(
            select(func.count()).select_from(User).where(User.role == "admin")
        )
        if existing_admin_count:
            return

        temporary_password = secrets.token_urlsafe(18)
        admin = User(
            email=settings.initial_admin_email,
            hashed_password=hash_password(temporary_password),
            role="admin",
            is_active=True,
            must_change_password=True,
        )
        session.add(admin)
        await session.commit()

        # Intentional: this is the only way to hand over the first admin
        # credential (no email/SMTP infra). Printed once; the account is
        # forced to change it on first login.
        logger.warning(
            "terratrain.admin_seeded",
            email=settings.initial_admin_email,
            temporary_password=temporary_password,
            action_required="log in and change this password immediately",
        )
