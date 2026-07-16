import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from terratrain.db.base import Base


class TrainingSession(Base):
    __tablename__ = "training_sessions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    athlete_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("athletes.id", ondelete="CASCADE"), nullable=False
    )
    intervals_activity_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    sport: Mapped[str] = mapped_column(String(32), nullable=False)
    start_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    distance_m: Mapped[float | None] = mapped_column(nullable=True)
    avg_power_watts: Mapped[float | None] = mapped_column(nullable=True)
    normalized_power_watts: Mapped[float | None] = mapped_column(nullable=True)
    avg_hr: Mapped[int | None] = mapped_column(Integer, nullable=True)
    max_hr: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tss: Mapped[float | None] = mapped_column(nullable=True)
    intensity_factor: Mapped[float | None] = mapped_column(nullable=True)
    elevation_gain_m: Mapped[float | None] = mapped_column(nullable=True)
    avg_speed_kmh: Mapped[float | None] = mapped_column(nullable=True)

    activity_data: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # Relationships
    athlete: Mapped["Athlete"] = relationship(back_populates="training_sessions")  # type: ignore[name-defined]  # noqa: F821
