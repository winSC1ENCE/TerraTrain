"""Fitness (PMC) data with Intervals.icu wellness fallback.

Primary path: compute CTL/ATL/TSB locally from synced training_sessions.
Fallback: athletes whose activities come from Strava get empty local data
(Strava's API terms block activity details), so we pull Intervals.icu's own
daily CTL/ATL from its wellness endpoint instead.
"""

from __future__ import annotations

from datetime import date, timedelta

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from terratrain.db.models.athlete import Athlete
from terratrain.db.models.session import TrainingSession
from terratrain.services.training_analytics import TrainingAnalytics

logger = structlog.get_logger()


async def get_fitness(athlete: Athlete, db: AsyncSession, days: int = 90) -> dict:
    """Return {"current": {...}, "series": [...]} for the athlete."""
    days = max(1, min(days, 365))

    result = await db.execute(
        select(TrainingSession).where(TrainingSession.athlete_id == athlete.id)
    )
    sessions = result.scalars().all()
    session_dicts = [
        {"start_date": s.start_date.date(), "tss": s.tss or 0.0} for s in sessions
    ]
    pmc = TrainingAnalytics.compute_pmc_series(session_dicts, days=days)

    has_local_data = any(p["tss"] > 0 for p in pmc["series"])
    if not has_local_data and athlete.intervals_api_key_encrypted:
        wellness_pmc = await _fitness_from_wellness(athlete, days)
        if wellness_pmc is not None:
            return wellness_pmc

    return pmc


async def _fitness_from_wellness(athlete: Athlete, days: int) -> dict | None:
    from terratrain.services.intervals_client import IntervalsClient

    try:
        client = IntervalsClient.from_athlete(athlete)
        today = date.today()
        entries = await client.get_wellness(
            oldest=today - timedelta(days=days), newest=today
        )
    except Exception as exc:
        logger.warning("fitness.wellness_fallback_failed", error=str(exc))
        return None

    if not entries:
        return None

    entries.sort(key=lambda e: e.get("id", ""))
    series = []
    prev_ctl: float | None = None
    prev_atl: float | None = None
    for e in entries:
        ctl = e.get("ctl")
        atl = e.get("atl")
        if ctl is None or atl is None:
            continue
        tsb = (prev_ctl - prev_atl) if prev_ctl is not None else (ctl - atl)
        series.append({
            "date": e.get("id", ""),
            "ctl": round(float(ctl), 1),
            "atl": round(float(atl), 1),
            "tsb": round(float(tsb), 1),
            "tss": round(float(e.get("ctlLoad") or 0.0), 1),
        })
        prev_ctl, prev_atl = float(ctl), float(atl)

    if not series:
        return None

    last = series[-1]
    week_ago_idx = max(0, len(series) - 8)
    current = {
        "ctl": last["ctl"],
        "atl": last["atl"],
        "tsb": last["tsb"],
        "ramp_rate_7d": round(last["ctl"] - series[week_ago_idx]["ctl"], 1),
    }
    return {"current": current, "series": series}
