import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from terratrain.api.deps import get_session
from terratrain.db.models.athlete import Athlete
from terratrain.db.models.workout import Workout
from terratrain.schemas.workout import WorkoutCreate, WorkoutResponse, WorkoutUpdate
from terratrain.services.intervals_client import IntervalsClient
from terratrain.services.security import decrypt_value

router = APIRouter()


@router.get("/{workout_id}", response_model=WorkoutResponse)
async def get_workout(
    workout_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
) -> Workout:
    workout = await session.get(Workout, workout_id)
    if not workout:
        raise HTTPException(status_code=404, detail="Workout not found")
    return workout


@router.put("/{workout_id}", response_model=WorkoutResponse)
async def update_workout(
    workout_id: uuid.UUID,
    body: WorkoutUpdate,
    session: AsyncSession = Depends(get_session),
) -> Workout:
    workout = await session.get(Workout, workout_id)
    if not workout:
        raise HTTPException(status_code=404, detail="Workout not found")

    for field, value in body.model_dump(exclude_none=True).items():
        setattr(workout, field, value)

    await session.commit()
    await session.refresh(workout)
    return workout


@router.delete("/{workout_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_workout(
    workout_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
) -> None:
    workout = await session.get(Workout, workout_id)
    if not workout:
        raise HTTPException(status_code=404, detail="Workout not found")
    await session.delete(workout)
    await session.commit()


@router.get("/athletes/{athlete_id}/workouts", response_model=list[WorkoutResponse])
async def list_workouts(
    athlete_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
) -> list[Workout]:
    result = await session.execute(
        select(Workout).where(Workout.athlete_id == athlete_id).order_by(Workout.created_at.desc())
    )
    return list(result.scalars().all())


@router.post("/{workout_id}/push", response_model=WorkoutResponse)
async def push_workout(
    workout_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
) -> Workout:
    workout = await session.get(Workout, workout_id)
    if not workout:
        raise HTTPException(status_code=404, detail="Workout not found")
    if not workout.structured_text:
        raise HTTPException(status_code=400, detail="Workout has no structured text to push")

    athlete = await session.get(Athlete, workout.athlete_id)
    if not athlete or not athlete.intervals_api_key_encrypted:
        raise HTTPException(status_code=400, detail="Athlete has no Intervals.icu API key")

    client = IntervalsClient.from_athlete(athlete)
    intervals_id = await client.push_workout(workout)
    workout.intervals_workout_id = intervals_id
    workout.status = "pushed"

    await session.commit()
    await session.refresh(workout)
    return workout
