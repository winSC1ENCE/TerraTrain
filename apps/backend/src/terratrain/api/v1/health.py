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
    ollama_status = "unknown"
    gemini_status = "unknown"

    # Check DB
    try:
        factory = get_session_factory()
        async with factory() as session:
            session: AsyncSession
            await session.execute(text("SELECT 1"))
    except Exception:
        db_status = "error"

    # Check Ollama
    if (
        settings.resolved_llm_provider == "ollama"
        or settings.resolved_embedding_provider == "ollama"
    ):
        ollama_status = "ok"
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.get(f"{settings.ollama_base_url}/api/tags")
                if resp.status_code != 200:
                    ollama_status = "error"
        except Exception:
            ollama_status = "error"

    # Check Gemini
    if (
        settings.resolved_llm_provider == "gemini"
        or settings.resolved_embedding_provider == "gemini"
    ):
        gemini_status = "ok"
        if not settings.gemini_api_key:
            gemini_status = "error"
        else:
            try:
                async with httpx.AsyncClient(timeout=5) as client:
                    resp = await client.get(
                        f"{settings.gemini_api_base}/models",
                        headers={"Authorization": f"Bearer {settings.gemini_api_key}"},
                    )
                    if resp.status_code != 200:
                        gemini_status = "error"
            except Exception:
                gemini_status = "error"

    degraded = False
    if db_status == "error":
        degraded = True
    if (
        settings.resolved_llm_provider == "ollama"
        or settings.resolved_embedding_provider == "ollama"
    ) and ollama_status == "error":
        degraded = True
    if (
        settings.resolved_llm_provider == "gemini"
        or settings.resolved_embedding_provider == "gemini"
    ) and gemini_status == "error":
        degraded = True

    status = "degraded" if degraded else "ok"
    return HealthResponse(
        status=status, database=db_status, ollama=ollama_status, gemini=gemini_status
    )
