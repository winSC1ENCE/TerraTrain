import uuid

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from terratrain.db.base import Base, TimestampMixin


class Route(Base, TimestampMixin):
    __tablename__ = "routes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    athlete_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("athletes.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    sport: Mapped[str] = mapped_column(String(32), nullable=False)
    gpx_data: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Metrics
    distance_m: Mapped[float] = mapped_column(nullable=False)
    elevation_gain_m: Mapped[float] = mapped_column(nullable=False)
    elevation_loss_m: Mapped[float] = mapped_column(nullable=False)
    max_elevation_m: Mapped[float | None] = mapped_column(nullable=True)
    min_elevation_m: Mapped[float | None] = mapped_column(nullable=True)

    # Terrain analysis (from gpx_analyzer.py)
    climb_profile: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    downhill_profile: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    terrain_score: Mapped[float | None] = mapped_column(nullable=True)
    surface_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    analysis: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    # Relationships
    athlete: Mapped["Athlete"] = relationship(back_populates="routes")  # type: ignore[name-defined]  # noqa: F821
    workouts: Mapped[list["Workout"]] = relationship(back_populates="route")  # type: ignore[name-defined]  # noqa: F821
