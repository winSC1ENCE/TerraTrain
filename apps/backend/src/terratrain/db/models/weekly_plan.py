import uuid

from sqlalchemy import Date, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from terratrain.db.base import Base, TimestampMixin


class WeeklyPlan(Base, TimestampMixin):
    __tablename__ = "weekly_plans"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    athlete_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("athletes.id", ondelete="CASCADE"), nullable=False
    )
    start_date: Mapped[object] = mapped_column(Date, nullable=False)  # Monday of the plan week
    mesocycle_type: Mapped[str] = mapped_column(String(16), nullable=False)  # "3-1" or "2-1"
    week_type: Mapped[str] = mapped_column(String(32), nullable=False)  # "load_1", "load_2", "load_3", "recovery"

    coach_rationale: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    athlete: Mapped["Athlete"] = relationship()  # type: ignore[name-defined]  # noqa: F821
    workouts: Mapped[list["Workout"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        back_populates="weekly_plan", cascade="all, delete-orphan"
    )
