import uuid
from datetime import date

from pydantic import BaseModel


class CoachingRequest(BaseModel):
    athlete_id: uuid.UUID
    route_id: uuid.UUID | None = None
    workout_type: str
    scheduled_date: date | None = None
    notes: str | None = None
    auto_push: bool = False
    provider: str | None = None


class CoachingSSEEvent(BaseModel):
    event: str  # thinking | tool_call | tool_result | workout_plan | error
    data: str
