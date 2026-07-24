from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from terratrain.db.base import Base


@pytest.fixture(scope="session")
def postgres_url() -> str:
    """One Postgres+pgvector container for the whole test session.

    Starting the container has no event-loop affinity (it's just a Docker
    process) — only an async SQLAlchemy engine bound to it does, so the
    engine itself stays function-scoped (see `engine` below). A session-
    scoped *async* engine would bind its asyncpg connections to whichever
    event loop was active when the fixture was created, which then breaks
    ("attached to a different loop") the moment a test runs on a different
    per-test loop, as pytest-asyncio creates by default.
    """
    from testcontainers.postgres import PostgresContainer

    with PostgresContainer("pgvector/pgvector:pg16") as pg:
        yield pg.get_connection_url().replace("psycopg2", "asyncpg")


@pytest_asyncio.fixture
async def engine(postgres_url):
    """A fresh async engine per test, bound to that test's own event loop."""
    eng = create_async_engine(postgres_url, echo=False)
    async with eng.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(Base.metadata.create_all)
        # The container (and its schema) is shared across the whole test
        # session, so start every test from a clean slate regardless of
        # what earlier tests committed.
        for table in reversed(Base.metadata.sorted_tables):
            await conn.execute(table.delete())
    yield eng
    await eng.dispose()


@pytest_asyncio.fixture
async def session(engine) -> AsyncGenerator[AsyncSession, None]:
    factory = async_sessionmaker(bind=engine, expire_on_commit=False)
    async with factory() as s:
        yield s
        await s.rollback()
