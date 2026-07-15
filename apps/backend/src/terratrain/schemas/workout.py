import uuid
from datetime import date, datetime

from pydantic import BaseModel, Field


class WorkoutPhase(BaseModel):
    name: str
    duration_min: float
    zone: str
    target_power_pct: float | None = None
    target_hr_zone: str | None = None
    description: str = ""
    repeat: int = 1


class WorkoutPlan(BaseModel):
    """Structured output from the coaching LLM — never contains raw DSL text."""

    name: str
    workout_type: str
    sport: str
    phases: list[WorkoutPhase]
    target_tss: float
    rationale: str
    coach_notes: str = ""


class WorkoutCreate(BaseModel):
    athlete_id: uuid.UUID
    route_id: uuid.UUID | None = None
    name: str
    sport: str
    workout_type: str
    scheduled_date: date | None = None
    coach_notes: str | None = None


class WorkoutUpdate(BaseModel):
    name: str | None = None
    structured_text: str | None = None
    coach_notes: str | None = None
    status: str | None = Field(
        default=None, pattern="^(draft|approved|pushed|completed|archived)$"
    )
    scheduled_date: date | None = None


class WorkoutResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    athlete_id: uuid.UUID
    route_id: uuid.UUID | None
    intervals_workout_id: str | None
    name: str
    sport: str
    workout_type: str
    scheduled_date: date | None
    duration_seconds: int | None
    target_tss: float | None
    structured_text: str | None
    llm_plan: dict
    llm_reasoning: str | None
    coach_notes: str | None
    status: str
    created_at: datetime
    updated_at: datetime
