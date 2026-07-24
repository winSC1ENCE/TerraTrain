import json
import uuid
from datetime import date

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from terratrain.api.deps import get_current_athlete, get_session
from terratrain.db.models.athlete import Athlete
from terratrain.db.models.weekly_plan import WeeklyPlan
from terratrain.schemas.weekly_plan import WeeklyPlanCreateRequest, WeeklyPlanResponse
from terratrain.services.intervals_client import IntervalsClient
from terratrain.services.mesocycle_detector import MesocycleDetector
from terratrain.services.weekly_coaching_agent import WeeklyCoachingAgent

logger = structlog.get_logger()
router = APIRouter()


async def _get_owned_plan(
    plan_id: uuid.UUID, athlete: Athlete, session: AsyncSession
) -> WeeklyPlan:
    result = await session.execute(
        select(WeeklyPlan)
        .options(selectinload(WeeklyPlan.workouts))
        .where(WeeklyPlan.id == plan_id)
    )
    plan = result.scalar_one_or_none()
    if not plan or plan.athlete_id != athlete.id:
        # 404 (not 403) so a foreign id doesn't confirm the resource exists.
        raise HTTPException(status_code=404, detail="Weekly plan not found")
    return plan


@router.get("/weekly-plans", response_model=list[WeeklyPlanResponse])
async def list_weekly_plans(
    athlete: Athlete = Depends(get_current_athlete),
    session: AsyncSession = Depends(get_session),
) -> list[WeeklyPlan]:
    result = await session.execute(
        select(WeeklyPlan)
        .options(selectinload(WeeklyPlan.workouts))
        .where(WeeklyPlan.athlete_id == athlete.id)
        .order_by(WeeklyPlan.start_date.desc())
    )
    return list(result.scalars().all())


@router.get("/weekly-plans/detect")
async def detect_mesocycle(
    start_date: date,
    mesocycle_type: str,
    athlete: Athlete = Depends(get_current_athlete),
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await MesocycleDetector.get_tss_history_and_recommendation(
        athlete=athlete,
        session=session,
        start_date=start_date,
        mesocycle_type=mesocycle_type,
    )


@router.post("/weekly-plans/generate")
async def generate_weekly_plan(
    body: WeeklyPlanCreateRequest,
    athlete: Athlete = Depends(get_current_athlete),
    session: AsyncSession = Depends(get_session),
) -> StreamingResponse:
    agent = WeeklyCoachingAgent(session=session)

    async def event_stream() -> object:
        async for event in agent.generate_week(athlete, body):
            yield f"event: {event['event']}\ndata: {json.dumps(event['data'])}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/weekly-plans/{plan_id}", response_model=WeeklyPlanResponse)
async def get_weekly_plan(
    plan_id: uuid.UUID,
    athlete: Athlete = Depends(get_current_athlete),
    session: AsyncSession = Depends(get_session),
) -> WeeklyPlan:
    return await _get_owned_plan(plan_id, athlete, session)


@router.delete("/weekly-plans/{plan_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_weekly_plan(
    plan_id: uuid.UUID,
    athlete: Athlete = Depends(get_current_athlete),
    session: AsyncSession = Depends(get_session),
) -> None:
    plan = await _get_owned_plan(plan_id, athlete, session)
    await session.delete(plan)
    await session.commit()


@router.post("/weekly-plans/{plan_id}/push")
async def push_weekly_plan(
    plan_id: uuid.UUID,
    athlete: Athlete = Depends(get_current_athlete),
    session: AsyncSession = Depends(get_session),
) -> dict:
    plan = await _get_owned_plan(plan_id, athlete, session)
    if not athlete.intervals_api_key_encrypted:
        raise HTTPException(status_code=400, detail="Athlete has no Intervals.icu API key")

    client = IntervalsClient.from_athlete(athlete)
    pushed_ids = []

    for w in plan.workouts:
        if w.status == "draft" and w.structured_text:
            try:
                intervals_id = await client.push_workout(w)
                w.intervals_workout_id = intervals_id
                w.status = "pushed"
                pushed_ids.append(str(w.id))
            except Exception as exc:
                logger.error("weekly_plan_push_item_failed", workout_id=w.id, error=str(exc))

    await session.commit()
    return {"pushed_workout_ids": pushed_ids}
