import uuid
from datetime import date, datetime

from pydantic import BaseModel, Field

from terratrain.constants import SPORT_PATTERN
from terratrain.schemas.workout import WorkoutResponse


class DailyScheduleInput(BaseModel):
    day_of_week: int  # 0 (Monday) to 6 (Sunday)
    duration_min: float
    sport: str | None = Field(default=None, pattern=SPORT_PATTERN)
    route_id: uuid.UUID | None = None
    notes: str | None = None


class WeeklyPlanCreateRequest(BaseModel):
    start_date: date
    mesocycle_type: str  # "3-1" or "2-1"
    week_type: str  # "load_1", "load_2", "load_3", "recovery"
    schedules: list[DailyScheduleInput]
    aggressiveness: int = Field(default=0, ge=-2, le=2)
    notes: str | None = None
    provider: str | None = None
    press_lap: bool = False
    funny_names: bool = False
    language: str | None = None


class WeeklyPlanResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    athlete_id: uuid.UUID
    start_date: date
    mesocycle_type: str
    week_type: str
    coach_rationale: str | None
    notes: str | None
    workouts: list[WorkoutResponse] = []
    created_at: datetime
    updated_at: datetime
