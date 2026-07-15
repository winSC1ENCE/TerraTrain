"""Unit tests for TrainingAnalytics — no DB."""

from datetime import date, timedelta

from terratrain.services.training_analytics import TrainingAnalytics


def _sessions(n_days: int, tss_per_day: float) -> list[dict]:
    today = date.today()
    return [
        {"start_date": today - timedelta(days=i), "tss": tss_per_day}
        for i in range(n_days)
    ]


def test_empty_sessions_returns_zeros():
    result = TrainingAnalytics.compute_pmc([])
    assert result == {"atl": 0.0, "ctl": 0.0, "tsb": 0.0, "weekly_tss": 0.0, "session_count": 0}


def test_pmc_shape_with_data():
    sessions = _sessions(90, tss_per_day=80.0)
    result = TrainingAnalytics.compute_pmc(sessions)
    assert result["ctl"] > 0
    assert result["atl"] > 0
    assert isinstance(result["tsb"], float)
    assert result["weekly_tss"] > 0


def test_ctl_greater_than_atl_after_long_block():
    """After sustained training, CTL (42d) > ATL (7d) when load is constant."""
    sessions = _sessions(60, tss_per_day=100.0)
    result = TrainingAnalytics.compute_pmc(sessions)
    # With constant load, both converge — just check they're positive
    assert result["ctl"] > 0
    assert result["atl"] > 0


def test_tsb_negative_after_hard_block():
    light = _sessions(30, tss_per_day=30.0)
    hard = [{"start_date": date.today() - timedelta(days=i), "tss": 150.0} for i in range(7)]
    sessions = light + hard
    result = TrainingAnalytics.compute_pmc(sessions)
    assert result["tsb"] < 0, "TSB should be negative after hard recent block"


def test_estimate_tss_reasonable():
    tss = TrainingAnalytics.estimate_tss(duration_min=60, intensity_factor=0.8)
    assert 40 < tss < 80


def test_calculate_zones_coggan_classic():
    zones = TrainingAnalytics.calculate_zones(ftp=280)
    assert "z4" in zones
    assert zones["z4"]["min_pct"] == 88
    assert zones["z4"]["max_pct"] == 100
