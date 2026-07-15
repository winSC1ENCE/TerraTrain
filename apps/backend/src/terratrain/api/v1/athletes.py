import uuid

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from terratrain.api.deps import get_session
from terratrain.db.models.athlete import Athlete
from terratrain.schemas.athlete import AthleteCreate, AthleteResponse, AthleteUpdate, SyncResponse
from terratrain.services.intervals_client import IntervalsClient
from terratrain.services.security import encrypt_value

logger = structlog.get_logger()
router = APIRouter()


@router.post("", response_model=AthleteResponse, status_code=status.HTTP_201_CREATED)
async def create_athlete(
    body: AthleteCreate,
    session: AsyncSession = Depends(get_session),
) -> Athlete:
    athlete = Athlete(
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
    await session.commit()
    await session.refresh(athlete)
    return athlete


@router.get("/{athlete_id}", response_model=AthleteResponse)
async def get_athlete(
    athlete_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
) -> Athlete:
    athlete = await session.get(Athlete, athlete_id)
    if not athlete:
        raise HTTPException(status_code=404, detail="Athlete not found")
    return athlete


@router.put("/{athlete_id}", response_model=AthleteResponse)
async def update_athlete(
    athlete_id: uuid.UUID,
    body: AthleteUpdate,
    session: AsyncSession = Depends(get_session),
) -> Athlete:
    athlete = await session.get(Athlete, athlete_id)
    if not athlete:
        raise HTTPException(status_code=404, detail="Athlete not found")

    for field, value in body.model_dump(exclude_none=True).items():
        if field == "intervals_api_key":
            athlete.intervals_api_key_encrypted = encrypt_value(value)
        else:
            setattr(athlete, field, value)

    await session.commit()
    await session.refresh(athlete)
    return athlete


@router.delete("/{athlete_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_athlete(
    athlete_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
) -> None:
    athlete = await session.get(Athlete, athlete_id)
    if not athlete:
        raise HTTPException(status_code=404, detail="Athlete not found")
    await session.delete(athlete)
    await session.commit()


@router.post("/{athlete_id}/sync", response_model=SyncResponse)
async def sync_athlete(
    athlete_id: uuid.UUID,
    days: int = 90,
    session: AsyncSession = Depends(get_session),
) -> SyncResponse:
    athlete = await session.get(Athlete, athlete_id)
    if not athlete:
        raise HTTPException(status_code=404, detail="Athlete not found")
    if not athlete.intervals_api_key_encrypted:
        raise HTTPException(status_code=400, detail="No Intervals.icu API key configured")

    client = IntervalsClient.from_athlete(athlete)
    result = await client.sync_to_db(athlete, session, days=days)
    return SyncResponse(**result)


@router.get("", response_model=list[AthleteResponse])
async def list_athletes(
    session: AsyncSession = Depends(get_session),
) -> list[Athlete]:
    result = await session.execute(select(Athlete))
    return list(result.scalars().all())
