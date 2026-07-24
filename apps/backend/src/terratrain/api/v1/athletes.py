from datetime import date as date_type

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from terratrain.api.deps import (
    get_current_active_user,
    get_current_athlete,
    get_session,
    require_admin,
)
from terratrain.db.models.athlete import Athlete
from terratrain.db.models.user import User
from terratrain.schemas.athlete import AthleteCreate, AthleteResponse, AthleteUpdate, SyncResponse
from terratrain.services.fitness_service import get_fitness as fitness
from terratrain.services.intervals_client import IntervalsClient
from terratrain.services.security import encrypt_value

logger = structlog.get_logger()
router = APIRouter()


@router.post("/me", response_model=AthleteResponse, status_code=status.HTTP_201_CREATED)
async def create_athlete(
    body: AthleteCreate,
    user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_session),
) -> Athlete:
    athlete = Athlete(
        user_id=user.id,
        intervals_user_id=body.intervals_user_id,
        name=body.name,
        sport=body.sport,
        ftp_watts=body.ftp_watts,
        threshold_pace_s_per_m=body.threshold_pace_s_per_m,
        lthr=body.lthr,
        max_hr=body.max_hr,
        resting_hr=body.resting_hr,
        weight_kg=body.weight_kg,
        vo2max=body.vo2max,
        intervals_api_key_encrypted=(
            encrypt_value(body.intervals_api_key) if body.intervals_api_key else None
        ),
    )
    session.add(athlete)
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="athlete profile already exists"
        ) from exc
    await session.refresh(athlete)
    return athlete


@router.get("/me", response_model=AthleteResponse)
async def get_athlete(athlete: Athlete = Depends(get_current_athlete)) -> Athlete:
    return athlete


@router.put("/me", response_model=AthleteResponse)
async def update_athlete(
    body: AthleteUpdate,
    athlete: Athlete = Depends(get_current_athlete),
    session: AsyncSession = Depends(get_session),
) -> Athlete:
    for field, value in body.model_dump(exclude_none=True).items():
        if field == "intervals_api_key":
            athlete.intervals_api_key_encrypted = encrypt_value(value)
        else:
            setattr(athlete, field, value)

    await session.commit()
    await session.refresh(athlete)
    return athlete


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
async def delete_athlete(
    athlete: Athlete = Depends(get_current_athlete),
    session: AsyncSession = Depends(get_session),
) -> None:
    await session.delete(athlete)
    await session.commit()


@router.post("/me/sync", response_model=SyncResponse)
async def sync_athlete(
    days: int = 90,
    athlete: Athlete = Depends(get_current_athlete),
    session: AsyncSession = Depends(get_session),
) -> SyncResponse:
    if not athlete.intervals_api_key_encrypted:
        raise HTTPException(status_code=400, detail="No Intervals.icu API key configured")

    client = IntervalsClient.from_athlete(athlete)
    result = await client.sync_to_db(athlete, session, days=days)
    return SyncResponse(**result)


@router.get("", response_model=list[AthleteResponse])
async def list_athletes(
    session: AsyncSession = Depends(get_session),
    _admin: User = Depends(require_admin),
) -> list[Athlete]:
    result = await session.execute(select(Athlete))
    return list(result.scalars().all())


@router.get("/me/fitness")
async def get_fitness_endpoint(
    days: int = 90,
    athlete: Athlete = Depends(get_current_athlete),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Daily PMC series (CTL/ATL/TSB) for the dashboard chart.

    Falls back to Intervals.icu wellness data for Strava-sourced athletes
    whose local sessions carry no TSS.
    """
    pmc = await fitness(athlete, session, days=days)
    return {
        "athlete_id": str(athlete.id),
        "as_of": date_type.today().isoformat(),
        **pmc,
    }
