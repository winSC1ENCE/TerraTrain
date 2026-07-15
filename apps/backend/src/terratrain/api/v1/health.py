import httpx
from fastapi import APIRouter
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from terratrain.config import get_settings
from terratrain.db.engine import get_session_factory
from terratrain.schemas.common import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(status="ok")


@router.get("/health/ready", response_model=HealthResponse)
async def readiness() -> HealthResponse:
    settings = get_settings()
    db_status = "ok"
    ollama_status = "ok"

    # Check DB
    try:
        factory = get_session_factory()
        async with factory() as session:
            session: AsyncSession
            await session.execute(text("SELECT 1"))
    except Exception:
        db_status = "error"

    # Check Ollama
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(f"{settings.ollama_base_url}/api/tags")
            if resp.status_code != 200:
                ollama_status = "error"
    except Exception:
        ollama_status = "error"

    status = "ok" if db_status == "ok" and ollama_status == "ok" else "degraded"
    return HealthResponse(status=status, database=db_status, ollama=ollama_status)
