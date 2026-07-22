"""Seed the database with a dev athlete fixture."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "apps/backend/src"))

from terratrain.db.engine import get_session_factory
from terratrain.db.models.athlete import Athlete


async def seed() -> None:
    factory = get_session_factory()
    async with factory() as session:
        from sqlalchemy import select

        existing = await session.execute(
            select(Athlete).where(Athlete.intervals_user_id == "i00000")
        )
        if existing.scalar_one_or_none():
            print("Dev athlete already exists — skipping seed.")
            return

        athlete = Athlete(
            intervals_user_id="i00000",
            name="Dev Athlete",
            sport="cycling",
            ftp_watts=280,
            weight_kg=70.0,
            lthr=165,
            max_hr=185,
            resting_hr=48,
            training_zones={
                "z1": {"name": "Active Recovery", "min_pct": 0, "max_pct": 55},
                "z2": {"name": "Endurance", "min_pct": 56, "max_pct": 75},
                "z3": {"name": "Tempo", "min_pct": 76, "max_pct": 87},
                "z4": {"name": "Threshold", "min_pct": 88, "max_pct": 100},
                "z5": {"name": "VO2 Max", "min_pct": 101, "max_pct": 118},
            },
        )
        session.add(athlete)
        await session.commit()
        print(f"Dev athlete created: {athlete.id}")


if __name__ == "__main__":
    asyncio.run(seed())
