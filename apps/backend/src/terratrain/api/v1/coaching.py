import json

import structlog
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from terratrain.api.deps import get_current_athlete, get_session
from terratrain.db.models.athlete import Athlete
from terratrain.db.models.route import Route
from terratrain.schemas.coaching import CoachingRequest
from terratrain.services.coaching_agent import CoachingAgent

logger = structlog.get_logger()
router = APIRouter()


@router.post("/generate")
async def generate_workout(
    body: CoachingRequest,
    athlete: Athlete = Depends(get_current_athlete),
    session: AsyncSession = Depends(get_session),
) -> StreamingResponse:
    route = None
    if body.route_id:
        route = await session.get(Route, body.route_id)
        if not route or route.athlete_id != athlete.id:
            # 404 (not 403) so a foreign id doesn't confirm the resource exists.
            raise HTTPException(status_code=404, detail="Route not found")

    if body.weekly_plan_id and body.scheduled_date:
        from datetime import timedelta
        from terratrain.db.models.weekly_plan import WeeklyPlan

        wp = await session.get(WeeklyPlan, body.weekly_plan_id)
        if wp and wp.athlete_id == athlete.id:
            end_date = wp.start_date + timedelta(days=6)
            if not (wp.start_date <= body.scheduled_date <= end_date):
                raise HTTPException(
                    status_code=400,
                    detail=f"Scheduled date must be within the weekly plan ({wp.start_date} to {end_date})",
                )

    agent = CoachingAgent(session=session)

    async def event_stream() -> object:
        async for event in agent.generate(
            athlete=athlete,
            route=route,
            workout_type=body.workout_type,
            sport=body.sport,
            aggressiveness=body.aggressiveness,
            scheduled_date=body.scheduled_date,
            notes=body.notes,
            auto_push=body.auto_push,
            provider=body.provider,
            press_lap=body.press_lap,
            load_policy=body.load_policy,
            weekly_plan_id=body.weekly_plan_id,
            source_workout_id=body.source_workout_id,
        ):
            yield f"event: {event['event']}\ndata: {json.dumps(event['data'])}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
