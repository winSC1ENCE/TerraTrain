"""Async httpx client for the Intervals.icu REST API.

Uses Basic Auth: username='API_KEY', password=<api_key>.
Retries on 429 / 5xx with exponential backoff via tenacity.
"""

from __future__ import annotations

from datetime import date, timedelta

import httpx
import structlog
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

from terratrain.config import get_settings
from terratrain.db.models.athlete import Athlete
from terratrain.services.security import decrypt_value

logger = structlog.get_logger()


def _is_retryable(exc: BaseException) -> bool:
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code in {429, 500, 502, 503, 504}
    return isinstance(exc, httpx.TransportError)


class IntervalsClient:
    def __init__(self, athlete_id: str, api_key: str) -> None:
        self._athlete_id = athlete_id
        self._api_key = api_key
        self._base = get_settings().intervals_api_base_url

    @classmethod
    def from_athlete(cls, athlete: Athlete) -> "IntervalsClient":
        if not athlete.intervals_api_key_encrypted:
            raise ValueError("Athlete has no Intervals.icu API key")
        api_key = decrypt_value(athlete.intervals_api_key_encrypted)
        return cls(athlete_id=athlete.intervals_user_id, api_key=api_key)

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            auth=("API_KEY", self._api_key),
            timeout=30,
            headers={"Accept": "application/json"},
        )

    @retry(
        retry=retry_if_exception(_is_retryable),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        stop=stop_after_attempt(4),
    )
    async def get_athlete_profile(self) -> dict:
        async with self._client() as c:
            resp = await c.get(f"{self._base}/athlete/{self._athlete_id}")
            resp.raise_for_status()
            return resp.json()

    @retry(
        retry=retry_if_exception(_is_retryable),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        stop=stop_after_attempt(4),
    )
    async def get_activities(self, oldest: date, newest: date) -> list[dict]:
        async with self._client() as c:
            resp = await c.get(
                f"{self._base}/athlete/{self._athlete_id}/activities",
                params={
                    "oldest": oldest.isoformat(),
                    "newest": newest.isoformat(),
                },
            )
            resp.raise_for_status()
            return resp.json()

    @retry(
        retry=retry_if_exception(_is_retryable),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        stop=stop_after_attempt(4),
    )
    async def get_wellness(self, oldest: date, newest: date) -> list[dict]:
        """Daily wellness entries incl. Intervals.icu's own CTL/ATL.

        This works even for Strava-sourced athletes: activity details are
        blocked by Strava's API terms, but Intervals.icu's derived fitness
        metrics are its own data and remain available.
        """
        async with self._client() as c:
            resp = await c.get(
                f"{self._base}/athlete/{self._athlete_id}/wellness",
                params={"oldest": oldest.isoformat(), "newest": newest.isoformat()},
            )
            resp.raise_for_status()
            return resp.json()

    @retry(
        retry=retry_if_exception(_is_retryable),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        stop=stop_after_attempt(4),
    )
    async def push_workout(self, workout: object) -> str:
        """Push a workout to Intervals.icu calendar and return the event ID."""
        payload = {
            "name": workout.name,  # type: ignore[attr-defined]
            "type": workout.sport.capitalize(),  # type: ignore[attr-defined]
            "description": workout.structured_text,  # type: ignore[attr-defined]
        }
        if workout.scheduled_date:  # type: ignore[attr-defined]
            payload["start_date_local"] = str(workout.scheduled_date)  # type: ignore[attr-defined]

        async with self._client() as c:
            resp = await c.post(
                f"{self._base}/athlete/{self._athlete_id}/events",
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()
            return str(data.get("id", ""))

    @staticmethod
    def _map_profile(profile: dict, sport: str) -> dict:
        """Map an Intervals.icu athlete profile to TerraTrain athlete fields.

        FTP/LTHR/max_hr are per-sport and live in `sportSettings`; weight and
        resting HR are top-level `icu_*` fields.
        """
        sport_types = {
            "cycling": {"Ride", "VirtualRide", "MountainBikeRide", "GravelRide", "TrackRide"},
            "running": {"Run", "VirtualRun", "TrailRun"},
        }
        wanted = sport_types.get(sport, {"Ride"})

        settings = profile.get("sportSettings") or []
        chosen = next(
            (s for s in settings if set(s.get("types") or []) & wanted),
            settings[0] if settings else None,
        )

        updates: dict = {
            "weight_kg": profile.get("icu_weight"),
            "resting_hr": profile.get("icu_resting_hr"),
        }
        if chosen:
            updates["ftp_watts"] = chosen.get("ftp")
            updates["lthr"] = chosen.get("lthr")
            updates["max_hr"] = chosen.get("max_hr")
        return updates

    async def sync_to_db(
        self, athlete: Athlete, session: object, days: int = 90
    ) -> dict:
        """Pull recent activities and upsert into training_sessions."""
        from datetime import timezone

        from sqlalchemy import select
        from sqlalchemy.ext.asyncio import AsyncSession

        from terratrain.db.models.session import TrainingSession

        db: AsyncSession = session  # type: ignore[assignment]

        today = date.today()
        oldest = today - timedelta(days=days)
        activities = await self.get_activities(oldest=oldest, newest=today)

        synced = 0
        for act in activities:
            activity_id = str(act.get("id", ""))
            existing = await db.execute(
                select(TrainingSession).where(
                    TrainingSession.intervals_activity_id == activity_id
                )
            )
            if existing.scalar_one_or_none():
                continue

            from datetime import datetime
            start_raw = act.get("start_date_local") or act.get("start_date", "")
            try:
                start_dt = datetime.fromisoformat(start_raw.rstrip("Z")).replace(
                    tzinfo=timezone.utc
                )
            except (ValueError, AttributeError):
                continue

            ts = TrainingSession(
                athlete_id=athlete.id,
                intervals_activity_id=activity_id,
                sport=act.get("type", "Ride").lower(),
                start_date=start_dt,
                duration_seconds=act.get("elapsed_time"),
                distance_m=act.get("distance"),
                avg_power_watts=act.get("average_watts"),
                normalized_power_watts=act.get("normalized_power"),
                avg_hr=act.get("average_heartrate"),
                max_hr=act.get("max_heartrate"),
                tss=act.get("training_load"),
                intensity_factor=act.get("intensity"),
                elevation_gain_m=act.get("total_elevation_gain"),
                avg_speed_kmh=(
                    act.get("average_speed", 0) * 3.6
                    if act.get("average_speed")
                    else None
                ),
                activity_data=act,
                created_at=datetime.now(tz=timezone.utc),
            )
            db.add(ts)
            synced += 1

        await db.commit()

        profile_updated = False
        try:
            profile = await self.get_athlete_profile()
            for field, value in self._map_profile(profile, athlete.sport).items():
                if value is not None:
                    setattr(athlete, field, value)
                    profile_updated = True
            if profile_updated:
                await db.commit()
        except Exception as exc:
            logger.warning("intervals.profile_sync_failed", error=str(exc))

        return {
            "sessions_synced": synced,
            "profile_updated": profile_updated,
            "message": f"Synced {synced} new sessions from last {days} days",
        }
