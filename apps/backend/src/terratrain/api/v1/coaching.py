import json

import structlog
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from terratrain.api.deps import get_session
from terratrain.db.models.athlete import Athlete
from terratrain.db.models.route import Route
from terratrain.schemas.coaching import CoachingRequest
from terratrain.services.coaching_agent import CoachingAgent

logger = structlog.get_logger()
router = APIRouter()


@router.post("/generate")
async def generate_workout(
    body: CoachingRequest,
    session: AsyncSession = Depends(get_session),
) -> StreamingResponse:
    athlete = await session.get(Athlete, body.athlete_id)
    if not athlete:
        raise HTTPException(status_code=404, detail="Athlete not found")

    route = None
    if body.route_id:
        route = await session.get(Route, body.route_id)
        if not route:
            raise HTTPException(status_code=404, detail="Route not found")

    agent = CoachingAgent(session=session)

    async def event_stream() -> object:
        async for event in agent.generate(
            athlete=athlete,
            route=route,
            workout_type=body.workout_type,
            scheduled_date=body.scheduled_date,
            notes=body.notes,
            auto_push=body.auto_push,
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
