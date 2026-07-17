import uuid
from datetime import date, datetime, time, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from terratrain.db.models.athlete import Athlete
from terratrain.db.models.session import TrainingSession


class MesocycleDetector:
    @staticmethod
    async def get_tss_history_and_recommendation(
        athlete: Athlete, session: AsyncSession, start_date: date, mesocycle_type: str
    ) -> dict:
        # Calculate weekly TSS starting W-4 to W-1
        history = []
        for i in range(4, 0, -1):
            w_start = start_date - timedelta(weeks=i)
            w_end = w_start + timedelta(days=6)

            # Create timezone-aware datetime range
            w_start_dt = datetime.combine(w_start, time.min).replace(tzinfo=timezone.utc)
            w_end_dt = datetime.combine(w_end, time.max).replace(tzinfo=timezone.utc)

            result = await session.execute(
                select(TrainingSession)
                .where(TrainingSession.athlete_id == athlete.id)
                .where(TrainingSession.start_date >= w_start_dt)
                .where(TrainingSession.start_date <= w_end_dt)
            )
            sessions = result.scalars().all()
            tss = sum(s.tss or 0.0 for s in sessions)
            history.append(
                {
                    "week_label": f"W-{i}",
                    "start_date": w_start.isoformat(),
                    "end_date": w_end.isoformat(),
                    "tss": round(tss, 1),
                }
            )

        w4_tss, w3_tss, w2_tss, w1_tss = [w["tss"] for w in history]

        rec = "load_1"
        reason = "Starting a new load cycle because W-1 training stress was low or default start."

        if mesocycle_type == "3-1":
            avg_prev = (w2_tss + w3_tss + w4_tss) / 3
            if avg_prev > 50 and w1_tss < avg_prev * 0.7:
                rec = "load_1"
                reason = f"Your W-1 TSS ({w1_tss:.0f}) represents a recovery drop compared to previous weeks (avg {avg_prev:.0f} TSS), starting Load Week 1."
            elif w1_tss > w2_tss > w3_tss > 0:
                rec = "recovery"
                reason = f"You completed 3 weeks of progressive loading (TSS: {w3_tss:.0f} -> {w2_tss:.0f} -> {w1_tss:.0f}). Time for a recovery week."
            elif w2_tss > w3_tss > 0:
                rec = "load_3"
                reason = f"Progressive overload detected over the last 2 weeks (TSS: {w3_tss:.0f} -> {w2_tss:.0f}). Suggest Load Week 3."
            else:
                rec = "load_2"
                reason = "Continuing progression into Load Week 2."
        else:  # "2-1"
            avg_prev = (w2_tss + w3_tss) / 2
            if avg_prev > 50 and w1_tss < avg_prev * 0.7:
                rec = "load_1"
                reason = f"Starting Load Week 1 following recovery (W-1 TSS: {w1_tss:.0f} vs avg {avg_prev:.0f} TSS)."
            elif w1_tss > w2_tss > 0:
                rec = "recovery"
                reason = f"You completed 2 weeks of progressive loading (TSS: {w2_tss:.0f} -> {w1_tss:.0f}). Recommend recovery week."
            else:
                rec = "load_2"
                reason = "Progression into Load Week 2."

        return {
            "history": history,
            "recommended_week_type": rec,
            "reasoning": reason,
        }
