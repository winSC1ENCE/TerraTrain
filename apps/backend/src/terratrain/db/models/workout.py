import uuid

from sqlalchemy import Date, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from terratrain.db.base import Base, TimestampMixin


class Workout(Base, TimestampMixin):
    __tablename__ = "workouts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    athlete_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("athletes.id", ondelete="CASCADE"), nullable=False
    )
    route_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("routes.id", ondelete="SET NULL"), nullable=True
    )
    intervals_workout_id: Mapped[str | None] = mapped_column(String(64), nullable=True)

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    sport: Mapped[str] = mapped_column(String(32), nullable=False)
    workout_type: Mapped[str] = mapped_column(String(64), nullable=False)
    # endurance | tempo | threshold | vo2max | race_simulation | recovery

    scheduled_date: Mapped[object] = mapped_column(Date, nullable=True)
    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    target_tss: Mapped[float | None] = mapped_column(nullable=True)

    structured_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    llm_plan: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    llm_reasoning: Mapped[str | None] = mapped_column(Text, nullable=True)
    coach_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    status: Mapped[str] = mapped_column(String(32), nullable=False, default="draft")
    # draft | approved | pushed | completed | archived

    # Relationships
    athlete: Mapped["Athlete"] = relationship(back_populates="workouts")  # type: ignore[name-defined]  # noqa: F821
    route: Mapped["Route | None"] = relationship(back_populates="workouts")  # type: ignore[name-defined]  # noqa: F821
