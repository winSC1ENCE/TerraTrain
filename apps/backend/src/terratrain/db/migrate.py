import asyncio
from pathlib import Path
import structlog
from alembic.config import Config
from alembic import command

logger = structlog.get_logger()


def apply_migrations() -> None:
    """Run Alembic migrations to upgrade the database schema to head."""
    ini_path = None
    for parent in Path(__file__).resolve().parents:
        candidate = parent / "alembic.ini"
        if candidate.exists():
            ini_path = candidate
            break

    if not ini_path:
        logger.warning("alembic.ini_not_found")
        return

    logger.info("alembic.apply_migrations.start", ini_path=str(ini_path))
    try:
        alembic_cfg = Config(str(ini_path))
        command.upgrade(alembic_cfg, "head")
        logger.info("alembic.apply_migrations.complete")
    except Exception as exc:
        logger.error("alembic.apply_migrations.error", error=str(exc))


async def run_migrations() -> None:
    """Run migrations asynchronously in a thread pool to avoid blocking the event loop."""
    await asyncio.to_thread(apply_migrations)
