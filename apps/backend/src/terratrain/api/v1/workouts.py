import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from terratrain.api.deps import get_current_athlete, get_session
from terratrain.db.models.athlete import Athlete
from terratrain.db.models.workout import Workout
from terratrain.schemas.workout import WorkoutResponse, WorkoutUpdate
from terratrain.services.intervals_client import IntervalsClient

router = APIRouter()


async def _get_owned_workout(
    workout_id: uuid.UUID, athlete: Athlete, session: AsyncSession
) -> Workout:
    workout = await session.get(Workout, workout_id)
    if not workout or workout.athlete_id != athlete.id:
        # 404 (not 403) so a foreign id doesn't confirm the resource exists.
        raise HTTPException(status_code=404, detail="Workout not found")
    return workout


@router.get("/workouts/{workout_id}", response_model=WorkoutResponse)
async def get_workout(
    workout_id: uuid.UUID,
    athlete: Athlete = Depends(get_current_athlete),
    session: AsyncSession = Depends(get_session),
) -> Workout:
    return await _get_owned_workout(workout_id, athlete, session)


@router.put("/workouts/{workout_id}", response_model=WorkoutResponse)
async def update_workout(
    workout_id: uuid.UUID,
    body: WorkoutUpdate,
    athlete: Athlete = Depends(get_current_athlete),
    session: AsyncSession = Depends(get_session),
) -> Workout:
    workout = await _get_owned_workout(workout_id, athlete, session)

    for field, value in body.model_dump(exclude_none=True).items():
        setattr(workout, field, value)

    await session.commit()
    await session.refresh(workout)
    return workout


@router.delete("/workouts/{workout_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_workout(
    workout_id: uuid.UUID,
    athlete: Athlete = Depends(get_current_athlete),
    session: AsyncSession = Depends(get_session),
) -> None:
    workout = await _get_owned_workout(workout_id, athlete, session)
    await session.delete(workout)
    await session.commit()


@router.get("/workouts", response_model=list[WorkoutResponse])
async def list_workouts(
    athlete: Athlete = Depends(get_current_athlete),
    session: AsyncSession = Depends(get_session),
) -> list[Workout]:
    result = await session.execute(
        select(Workout).where(Workout.athlete_id == athlete.id).order_by(Workout.created_at.desc())
    )
    return list(result.scalars().all())


@router.post("/workouts/{workout_id}/push", response_model=WorkoutResponse)
async def push_workout(
    workout_id: uuid.UUID,
    athlete: Athlete = Depends(get_current_athlete),
    session: AsyncSession = Depends(get_session),
) -> Workout:
    workout = await _get_owned_workout(workout_id, athlete, session)
    if not workout.structured_text:
        raise HTTPException(status_code=400, detail="Workout has no structured text to push")
    if not athlete.intervals_api_key_encrypted:
        raise HTTPException(status_code=400, detail="Athlete has no Intervals.icu API key")

    client = IntervalsClient.from_athlete(athlete)
    intervals_id = await client.push_workout(workout)
    workout.intervals_workout_id = intervals_id
    workout.status = "pushed"

    await session.commit()
    await session.refresh(workout)
    return workout
