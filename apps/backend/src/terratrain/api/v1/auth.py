import structlog
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from terratrain.api.deps import get_session
from terratrain.config import get_settings
from terratrain.services.strava_client import StravaClient

logger = structlog.get_logger()
router = APIRouter()


@router.get("/strava/authorize")
async def strava_authorize(athlete_id: str) -> RedirectResponse:
    settings = get_settings()
    if not settings.strava_client_id:
        raise HTTPException(status_code=501, detail="Strava integration not configured")

    url = StravaClient.build_auth_url(
        client_id=settings.strava_client_id,
        redirect_uri=settings.strava_redirect_uri,
        state=athlete_id,
    )
    return RedirectResponse(url=url)


@router.get("/strava/callback")
async def strava_callback(
    code: str,
    state: str,
    session: AsyncSession = Depends(get_session),
) -> dict:
    settings = get_settings()
    client = StravaClient(
        client_id=settings.strava_client_id,
        client_secret=settings.strava_client_secret,
    )
    await client.exchange_code(code=code, athlete_id=state, db_session=session)
    return {"status": "connected", "athlete_id": state}
