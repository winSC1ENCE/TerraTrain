from datetime import date
from unittest.mock import AsyncMock, MagicMock

import pytest

from terratrain.db.models.athlete import Athlete
from terratrain.db.models.session import TrainingSession
from terratrain.services.mesocycle_detector import MesocycleDetector


@pytest.mark.anyio
async def test_mesocycle_detector_3_1_progressive_load():
    athlete = Athlete(id=MagicMock(), name="Test Athlete", sport="cycling")
    session = AsyncMock()

    s4 = MagicMock(spec=TrainingSession)
    s4.tss = 0.0
    s3 = MagicMock(spec=TrainingSession)
    s3.tss = 100.0
    s2 = MagicMock(spec=TrainingSession)
    s2.tss = 200.0
    s1 = MagicMock(spec=TrainingSession)
    s1.tss = 300.0

    r4 = MagicMock()
    r4.scalars.return_value.all.return_value = [s4]
    r3 = MagicMock()
    r3.scalars.return_value.all.return_value = [s3]
    r2 = MagicMock()
    r2.scalars.return_value.all.return_value = [s2]
    r1 = MagicMock()
    r1.scalars.return_value.all.return_value = [s1]

    empty_wk = MagicMock()
    empty_wk.scalars.return_value.all.return_value = []

    session.execute.side_effect = [r4, empty_wk, r3, empty_wk, r2, empty_wk, r1, empty_wk]

    res = await MesocycleDetector.get_tss_history_and_recommendation(
        athlete=athlete,
        session=session,
        start_date=date(2026, 7, 20),
        mesocycle_type="3-1",
    )

    assert res["recommended_week_type"] == "recovery"
    assert "progressive loading" in res["reasoning"].lower()


@pytest.mark.anyio
async def test_mesocycle_detector_3_1_after_recovery():
    athlete = Athlete(id=MagicMock(), name="Test Athlete", sport="cycling")
    session = AsyncMock()

    s4 = MagicMock(spec=TrainingSession)
    s4.tss = 300.0
    s3 = MagicMock(spec=TrainingSession)
    s3.tss = 350.0
    s2 = MagicMock(spec=TrainingSession)
    s2.tss = 400.0
    s1 = MagicMock(spec=TrainingSession)
    s1.tss = 100.0

    r4 = MagicMock()
    r4.scalars.return_value.all.return_value = [s4]
    r3 = MagicMock()
    r3.scalars.return_value.all.return_value = [s3]
    r2 = MagicMock()
    r2.scalars.return_value.all.return_value = [s2]
    r1 = MagicMock()
    r1.scalars.return_value.all.return_value = [s1]

    empty_wk = MagicMock()
    empty_wk.scalars.return_value.all.return_value = []

    session.execute.side_effect = [r4, empty_wk, r3, empty_wk, r2, empty_wk, r1, empty_wk]

    res = await MesocycleDetector.get_tss_history_and_recommendation(
        athlete=athlete,
        session=session,
        start_date=date(2026, 7, 20),
        mesocycle_type="3-1",
    )

    assert res["recommended_week_type"] == "load_1"
    assert "recovery drop" in res["reasoning"].lower()


@pytest.mark.anyio
async def test_mesocycle_detector_week_selection_past_4_weeks():
    athlete = Athlete(id=MagicMock(), name="Test Athlete", sport="cycling")
    session = AsyncMock()

    empty_res = MagicMock()
    empty_res.scalars.return_value.all.return_value = []

    # 4 weeks history * 2 queries per week = 8 calls
    session.execute.side_effect = [empty_res] * 8

    # Start date is Monday Aug 3, 2026 (ISO Week 32)
    res = await MesocycleDetector.get_tss_history_and_recommendation(
        athlete=athlete,
        session=session,
        start_date=date(2026, 8, 3),
        mesocycle_type="3-1",
    )

    assert res["selected_week"]["week_number"] == 32
    assert res["selected_week"]["start_date"] == "2026-08-03"
    assert res["selected_week"]["end_date"] == "2026-08-09"

    past_week_numbers = [h["week_number"] for h in res["history"]]
    assert past_week_numbers == [28, 29, 30, 31]
    assert res["history"][3]["week_label"] == "KW 31"
    assert res["history"][2]["week_label"] == "KW 30"
    assert res["history"][1]["week_label"] == "KW 29"
    assert res["history"][0]["week_label"] == "KW 28"

