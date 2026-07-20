import uuid
from datetime import date, datetime, time, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from terratrain.db.models.athlete import Athlete
from terratrain.db.models.session import TrainingSession
from terratrain.db.models.workout import Workout


class MesocycleDetector:
    @staticmethod
    async def get_tss_history_and_recommendation(
        athlete: Athlete, session: AsyncSession, start_date: date, mesocycle_type: str
    ) -> dict:
        # 1. Fetch live daily load directly from Intervals.icu REST API wellness endpoint
        wellness_by_date: dict[str, float] = {}
        if athlete.intervals_api_key_encrypted and athlete.intervals_user_id:
            try:
                from terratrain.services.intervals_client import IntervalsClient
                client = IntervalsClient.from_athlete(athlete)
                oldest = start_date - timedelta(weeks=4)
                newest = start_date - timedelta(days=1)
                wellness_list = await client.get_wellness(oldest=oldest, newest=newest)
                for w in wellness_list:
                    day_id = str(w.get("id"))
                    load = w.get("load") or w.get("ctlLoad") or 0.0
                    wellness_by_date[day_id] = float(load)
            except Exception:
                pass

        # Calculate weekly TSS starting W-4 to W-1
        history = []
        for i in range(4, 0, -1):
            w_start = start_date - timedelta(weeks=i)
            w_end = w_start + timedelta(days=6)

            # Primary: Sum daily load from Intervals.icu REST API
            api_tss = 0.0
            for d in range(7):
                day_str = (w_start + timedelta(days=d)).strftime("%Y-%m-%d")
                api_tss += wellness_by_date.get(day_str, 0.0)

            # Secondary fallback: Local TrainingSession and Workout tables
            w_start_dt = datetime.combine(w_start, time.min).replace(tzinfo=timezone.utc)
            w_end_dt = datetime.combine(w_end, time.max).replace(tzinfo=timezone.utc)

            result = await session.execute(
                select(TrainingSession)
                .where(TrainingSession.athlete_id == athlete.id)
                .where(TrainingSession.start_date >= w_start_dt)
                .where(TrainingSession.start_date <= w_end_dt)
            )
            sessions = result.scalars().all()
            session_tss = sum(s.tss if s.tss is not None else (50.0 if sessions else 0.0) for s in sessions)

            res_wk = await session.execute(
                select(Workout)
                .where(Workout.athlete_id == athlete.id)
                .where(Workout.scheduled_date >= w_start)
                .where(Workout.scheduled_date <= w_end)
            )
            workouts = res_wk.scalars().all()
            workout_tss = sum(w.target_tss or 0.0 for w in workouts)

            final_tss = max(api_tss, session_tss, workout_tss)
            history.append(
                {
                    "week_label": f"W-{i}",
                    "start_date": w_start.isoformat(),
                    "end_date": w_end.isoformat(),
                    "tss": round(final_tss, 1),
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
