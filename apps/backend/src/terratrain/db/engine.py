from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from terratrain.config import get_settings
from terratrain.db.base import Base

_engine = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def get_engine() -> object:
    global _engine
    if _engine is None:
        settings = get_settings()
        _engine = create_async_engine(
            settings.database_url,
            pool_size=settings.database_pool_size,
            max_overflow=settings.database_pool_max_overflow,
            echo=settings.app_env == "development",
        )
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(
            bind=get_engine(),  # type: ignore[arg-type]
            class_=AsyncSession,
            expire_on_commit=False,
        )
    return _session_factory


async def create_db_and_tables() -> None:
    engine = get_engine()
    async with engine.begin() as conn:  # type: ignore[union-attr]
        await conn.run_sync(Base.metadata.create_all)


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    factory = get_session_factory()
    async with factory() as session:
        yield session
