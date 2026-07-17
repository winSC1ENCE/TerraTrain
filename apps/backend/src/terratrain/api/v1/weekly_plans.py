import json
from datetime import date
import uuid

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from terratrain.api.deps import get_session
from terratrain.db.models.athlete import Athlete
from terratrain.db.models.weekly_plan import WeeklyPlan
from terratrain.schemas.weekly_plan import WeeklyPlanCreateRequest, WeeklyPlanResponse
from terratrain.services.intervals_client import IntervalsClient
from terratrain.services.mesocycle_detector import MesocycleDetector
from terratrain.services.weekly_coaching_agent import WeeklyCoachingAgent

logger = structlog.get_logger()
router = APIRouter()


@router.get("/athletes/{athlete_id}/weekly-plans/detect")
async def detect_mesocycle(
    athlete_id: uuid.UUID,
    start_date: date,
    mesocycle_type: str,
    session: AsyncSession = Depends(get_session),
) -> dict:
    athlete = await session.get(Athlete, athlete_id)
    if not athlete:
        raise HTTPException(status_code=404, detail="Athlete not found")

    return await MesocycleDetector.get_tss_history_and_recommendation(
        athlete=athlete,
        session=session,
        start_date=start_date,
        mesocycle_type=mesocycle_type,
    )


@router.post("/weekly-plans/generate")
async def generate_weekly_plan(
    body: WeeklyPlanCreateRequest,
    session: AsyncSession = Depends(get_session),
) -> StreamingResponse:
    athlete = await session.get(Athlete, body.athlete_id)
    if not athlete:
        raise HTTPException(status_code=404, detail="Athlete not found")

    agent = WeeklyCoachingAgent(session=session)

    async def event_stream() -> object:
        async for event in agent.generate_week(body):
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
    session: AsyncSession = Depends(get_session),
) -> WeeklyPlan:
    result = await session.execute(
        select(WeeklyPlan)
        .options(selectinload(WeeklyPlan.workouts))
        .where(WeeklyPlan.id == plan_id)
    )
    plan = result.scalar_one_or_none()
    if not plan:
        raise HTTPException(status_code=404, detail="Weekly plan not found")
    return plan


@router.delete("/weekly-plans/{plan_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_weekly_plan(
    plan_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
) -> None:
    plan = await session.get(WeeklyPlan, plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Weekly plan not found")
    await session.delete(plan)
    await session.commit()


@router.post("/weekly-plans/{plan_id}/push")
async def push_weekly_plan(
    plan_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
) -> dict:
    result = await session.execute(
        select(WeeklyPlan)
        .options(selectinload(WeeklyPlan.workouts))
        .where(WeeklyPlan.id == plan_id)
    )
    plan = result.scalar_one_or_none()
    if not plan:
        raise HTTPException(status_code=404, detail="Weekly plan not found")

    athlete = await session.get(Athlete, plan.athlete_id)
    if not athlete or not athlete.intervals_api_key_encrypted:
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
