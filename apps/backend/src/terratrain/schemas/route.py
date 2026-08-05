import uuid
from datetime import datetime

from pydantic import BaseModel


class ClimbSegment(BaseModel):
    start_km: float
    end_km: float
    avg_grade_pct: float
    max_grade_pct: float
    length_m: float
    elevation_gain_m: float
    vam: float | None = None
    category: str | None = None  # hc | cat1 | cat2 | cat3 | cat4


class DescentSegment(BaseModel):
    start_km: float
    end_km: float
    avg_grade_pct: float
    min_grade_pct: float
    length_m: float
    elevation_loss_m: float


class RouteResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    athlete_id: uuid.UUID
    name: str
    sport: str
    distance_m: float
    elevation_gain_m: float
    elevation_loss_m: float
    max_elevation_m: float | None
    min_elevation_m: float | None
    climb_profile: list[dict]
    downhill_profile: list[dict] = []
    terrain_score: float | None
    surface_type: str | None
    analysis: dict
    created_at: datetime


class RouteUpdateRequest(BaseModel):
    name: str

