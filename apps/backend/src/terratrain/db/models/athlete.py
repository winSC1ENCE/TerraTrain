import uuid

from sqlalchemy import String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from terratrain.db.base import Base, TimestampMixin


class Athlete(Base, TimestampMixin):
    __tablename__ = "athletes"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    intervals_user_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    strava_athlete_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    sport: Mapped[str] = mapped_column(String(32), nullable=False)  # cycling|running|triathlon

    # Physiological parameters
    ftp_watts: Mapped[int | None] = mapped_column(nullable=True)
    threshold_pace_s_per_m: Mapped[float | None] = mapped_column(nullable=True)
    lthr: Mapped[int | None] = mapped_column(nullable=True)
    max_hr: Mapped[int | None] = mapped_column(nullable=True)
    resting_hr: Mapped[int | None] = mapped_column(nullable=True)
    weight_kg: Mapped[float | None] = mapped_column(nullable=True)
    vo2max: Mapped[float | None] = mapped_column(nullable=True)

    training_zones: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    intervals_api_key_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    routes: Mapped[list["Route"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        back_populates="athlete", cascade="all, delete-orphan"
    )
    workouts: Mapped[list["Workout"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        back_populates="athlete", cascade="all, delete-orphan"
    )
    training_sessions: Mapped[list["TrainingSession"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        back_populates="athlete", cascade="all, delete-orphan"
    )
    strava_token: Mapped["StravaToken | None"] = relationship(  # type: ignore[name-defined]  # noqa: F821
        back_populates="athlete", cascade="all, delete-orphan", uselist=False
    )
