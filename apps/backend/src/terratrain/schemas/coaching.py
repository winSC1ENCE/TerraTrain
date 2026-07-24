import uuid
from datetime import date

from pydantic import BaseModel, Field

from terratrain.constants import SPORT_PATTERN


class CoachingRequest(BaseModel):
    route_id: uuid.UUID | None = None
    workout_type: str
    sport: str | None = Field(default=None, pattern=SPORT_PATTERN)
    aggressiveness: int = Field(default=0, ge=-2, le=2)
    scheduled_date: date | None = None
    notes: str | None = None
    auto_push: bool = False
    provider: str | None = None
    press_lap: bool = False


class CoachingSSEEvent(BaseModel):
    event: str  # thinking | tool_call | tool_result | workout_plan | error
    data: str
