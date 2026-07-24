import uuid
from datetime import date, datetime

from pydantic import BaseModel, Field

from terratrain.constants import SPORT_PATTERN


class WorkoutPhase(BaseModel):
    name: str
    duration_min: float
    zone: str
    target_power_pct: float | None = None
    target_hr_zone: str | None = None
    target_cadence_rpm: int | None = None
    description: str = ""
    repeat: int = 1


class StrengthExercise(BaseModel):
    """One exercise within a weight-training workout (sets/reps/RPE, not phases)."""

    name: str
    sets: int
    reps: int
    rpe: float | None = None
    rest_seconds: int | None = None
    description: str = ""


class WorkoutPlan(BaseModel):
    """Structured output from the coaching LLM — never contains raw DSL text."""

    name: str
    workout_type: str
    sport: str = Field(pattern=SPORT_PATTERN)
    phases: list[WorkoutPhase] = []
    exercises: list[StrengthExercise] = []
    target_tss: float = 0.0
    rationale: str
    coach_notes: str = ""


class WorkoutCreate(BaseModel):
    athlete_id: uuid.UUID
    route_id: uuid.UUID | None = None
    name: str
    sport: str = Field(pattern=SPORT_PATTERN)
    workout_type: str
    scheduled_date: date | None = None
    coach_notes: str | None = None


class WorkoutUpdate(BaseModel):
    name: str | None = None
    sport: str | None = Field(default=None, pattern=SPORT_PATTERN)
    structured_text: str | None = None
    # When set, the "- Press lap" first line is added/removed in structured_text
    # to match (see WorkoutFormatter.apply_press_lap) — the client only flips
    # the flag, the server keeps the text in sync.
    press_lap: bool | None = None
    coach_notes: str | None = None
    status: str | None = Field(default=None, pattern="^(draft|approved|pushed|completed|archived)$")
    scheduled_date: date | None = None


class WorkoutResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    athlete_id: uuid.UUID
    route_id: uuid.UUID | None
    weekly_plan_id: uuid.UUID | None = None
    intervals_workout_id: str | None
    name: str
    sport: str
    workout_type: str
    scheduled_date: date | None
    duration_seconds: int | None
    target_tss: float | None
    structured_text: str | None
    press_lap: bool
    llm_plan: dict
    llm_reasoning: str | None
    coach_notes: str | None
    status: str
    created_at: datetime
    updated_at: datetime
