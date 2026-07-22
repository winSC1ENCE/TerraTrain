import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from terratrain.constants import SPORT_PATTERN


class AthleteCreate(BaseModel):
    intervals_user_id: str
    name: str
    sport: str = Field(pattern=SPORT_PATTERN)
    ftp_watts: int | None = None
    threshold_pace_s_per_m: float | None = None
    css_pace_s_per_100m: float | None = None
    lthr: int | None = None
    max_hr: int | None = None
    resting_hr: int | None = None
    weight_kg: float | None = None
    vo2max: float | None = None
    intervals_api_key: str | None = None


class AthleteUpdate(BaseModel):
    name: str | None = None
    sport: str | None = Field(default=None, pattern=SPORT_PATTERN)
    ftp_watts: int | None = None
    threshold_pace_s_per_m: float | None = None
    css_pace_s_per_100m: float | None = None
    lthr: int | None = None
    max_hr: int | None = None
    resting_hr: int | None = None
    weight_kg: float | None = None
    vo2max: float | None = None
    intervals_api_key: str | None = None


class AthleteResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    intervals_user_id: str
    name: str
    sport: str
    ftp_watts: int | None
    threshold_pace_s_per_m: float | None
    css_pace_s_per_100m: float | None
    lthr: int | None
    max_hr: int | None
    resting_hr: int | None
    weight_kg: float | None
    vo2max: float | None
    training_zones: dict
    created_at: datetime
    updated_at: datetime


class SyncResponse(BaseModel):
    sessions_synced: int
    profile_updated: bool
    message: str
