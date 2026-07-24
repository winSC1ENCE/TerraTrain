"""Training load analytics using Polars.

Computes ATL, CTL, TSB (the Performance Management Chart) from
a list of training sessions — pure Polars, no pandas.

ATL (Acute Training Load): 7-day exponential moving average of TSS
CTL (Chronic Training Load): 42-day exponential moving average of TSS
TSB (Training Stress Balance): CTL - ATL (form indicator)
"""

from __future__ import annotations

from datetime import date, timedelta

import polars as pl


class TrainingAnalytics:
    ATL_DAYS = 7
    CTL_DAYS = 42

    @staticmethod
    def compute_pmc(sessions: list[dict]) -> dict:
        """Compute current ATL, CTL, TSB from raw session dicts.

        Args:
            sessions: list of dicts with keys {start_date, tss}

        Returns:
            dict with atl, ctl, tsb, weekly_tss, session_count
        """
        if not sessions:
            return {"atl": 0.0, "ctl": 0.0, "tsb": 0.0, "weekly_tss": 0.0, "session_count": 0}

        df = pl.DataFrame(sessions).with_columns(
            pl.col("start_date").cast(pl.Date).alias("date"),
            pl.col("tss").fill_null(0.0).alias("tss"),
        )

        # Build daily TSS series from the earliest session to today
        min_date = df["date"].min()
        today = date.today()
        all_dates = pl.date_range(min_date, today, interval="1d", eager=True).alias("date")
        daily = pl.DataFrame({"date": all_dates})

        daily_tss = df.group_by("date").agg(pl.col("tss").sum().alias("tss")).sort("date")

        df_full = (
            daily.join(daily_tss, on="date", how="left")
            .with_columns(pl.col("tss").fill_null(0.0))
            .sort("date")
        )

        tss_list = df_full["tss"].to_list()
        atl_list = TrainingAnalytics._ema(tss_list, TrainingAnalytics.ATL_DAYS)
        ctl_list = TrainingAnalytics._ema(tss_list, TrainingAnalytics.CTL_DAYS)

        atl = atl_list[-1] if atl_list else 0.0
        ctl = ctl_list[-1] if ctl_list else 0.0
        tsb = ctl - atl

        seven_days_ago = today - timedelta(days=7)
        weekly_df = df.filter(pl.col("date") >= seven_days_ago)
        weekly_tss = float(weekly_df["tss"].sum())

        return {
            "atl": round(atl, 1),
            "ctl": round(ctl, 1),
            "tsb": round(tsb, 1),
            "weekly_tss": round(weekly_tss, 1),
            "session_count": len(sessions),
        }

    @staticmethod
    def compute_pmc_series(sessions: list[dict], days: int = 90) -> dict:
        """Compute a gapless daily PMC series for charting.

        Args:
            sessions: list of dicts with keys {start_date, tss}
            days: how many trailing days of series to return

        Returns:
            dict with `current` (ctl/atl/tsb/ramp_rate_7d) and `series`
            (ascending, one entry per calendar day, rest days tss=0).
        """
        today = date.today()
        if not sessions:
            return {
                "current": {"ctl": 0.0, "atl": 0.0, "tsb": 0.0, "ramp_rate_7d": 0.0},
                "series": [],
            }

        df = pl.DataFrame(sessions).with_columns(
            pl.col("start_date").cast(pl.Date).alias("date"),
            pl.col("tss").fill_null(0.0).alias("tss"),
        )

        # Gapless daily TSS from earliest session to today (EMA warm-up included)
        min_date = df["date"].min()
        all_dates = pl.date_range(min_date, today, interval="1d", eager=True).alias("date")
        daily_tss = df.group_by("date").agg(pl.col("tss").sum().alias("tss")).sort("date")
        df_full = (
            pl.DataFrame({"date": all_dates})
            .join(daily_tss, on="date", how="left")
            .with_columns(pl.col("tss").fill_null(0.0))
            .sort("date")
        )

        dates = df_full["date"].to_list()
        tss_list = df_full["tss"].to_list()
        atl_list = TrainingAnalytics._ema(tss_list, TrainingAnalytics.ATL_DAYS)
        ctl_list = TrainingAnalytics._ema(tss_list, TrainingAnalytics.CTL_DAYS)

        # TSB convention: form for day N uses the previous day's CTL/ATL
        series = []
        for i, d in enumerate(dates):
            prev = max(0, i - 1)
            series.append(
                {
                    "date": d.isoformat(),
                    "ctl": round(ctl_list[i], 1),
                    "atl": round(atl_list[i], 1),
                    "tsb": round(ctl_list[prev] - atl_list[prev], 1),
                    "tss": round(tss_list[i], 1),
                }
            )

        # Trim to requested window (after EMA warm-up over full history)
        series = series[-days:]

        ctl_now = ctl_list[-1]
        ramp_idx = max(0, len(ctl_list) - 8)
        current = {
            "ctl": round(ctl_now, 1),
            "atl": round(atl_list[-1], 1),
            "tsb": series[-1]["tsb"] if series else 0.0,
            "ramp_rate_7d": round(ctl_now - ctl_list[ramp_idx], 1),
        }
        return {"current": current, "series": series}

    @staticmethod
    def _ema(values: list[float], days: int) -> list[float]:
        """Exponential moving average with a decay constant of 1/days."""
        if not values:
            return []
        k = 1.0 / days
        result = [values[0]]
        for v in values[1:]:
            result.append(result[-1] * (1 - k) + v * k)
        return result

    @staticmethod
    def estimate_tss(duration_min: float, intensity_factor: float) -> float:
        """TSS = (duration_sec × NP × IF) / (FTP × 3600) × 100
        Simplified: TSS = duration_h × IF² × 100
        """
        return round((duration_min / 60) * (intensity_factor**2) * 100, 1)

    @staticmethod
    def calculate_zones(ftp: int, model: str = "coggan_classic") -> dict:
        """Return power zone boundaries as percentage of FTP (cycling)."""
        if model == "coggan_classic":
            return {
                "z1": {"name": "Active Recovery", "min_pct": 0, "max_pct": 55},
                "z2": {"name": "Endurance", "min_pct": 56, "max_pct": 75},
                "z3": {"name": "Tempo", "min_pct": 76, "max_pct": 87},
                "z4": {"name": "Threshold", "min_pct": 88, "max_pct": 100},
                "z5": {"name": "VO2 Max", "min_pct": 101, "max_pct": 118},
                "z6": {"name": "Anaerobic", "min_pct": 119, "max_pct": 150},
                "z7": {"name": "Neuromuscular", "min_pct": 151, "max_pct": 999},
            }
        raise ValueError(f"Unknown zone model: {model}")

    # (name, min_pct, max_pct) — bounds table shared by the threshold-relative
    # pace/HR zone calculators below. Keeping these as plain (str, float, float)
    # tuples (rather than mixed-type dict literals) lets mypy track the numeric
    # types correctly through the arithmetic that follows.
    _RUNNING_PACE_ZONE_BOUNDS: tuple[tuple[str, str, float, float], ...] = (
        ("z1", "Recovery", 130.0, 999.0),
        ("z2", "Endurance", 114.0, 129.0),
        ("z3", "Tempo", 106.0, 113.0),
        ("z4", "Threshold", 99.0, 105.0),
        ("z5", "VO2max", 85.0, 98.0),
    )
    _SWIM_CSS_ZONE_BOUNDS: tuple[tuple[str, str, float, float], ...] = (
        ("z1", "Recovery", 121.0, 999.0),
        ("z2", "Endurance", 111.0, 120.0),
        ("z3", "Threshold (CSS)", 100.0, 110.0),
        ("z4", "VO2max", 90.0, 99.0),
        ("z5", "Sprint", 0.0, 89.0),
    )
    _HR_ZONE_BOUNDS: tuple[tuple[str, str, float, float], ...] = (
        ("z1", "Recovery", 0.0, 80.0),
        ("z2", "Endurance", 81.0, 89.0),
        ("z3", "Tempo", 90.0, 93.0),
        ("z4", "Threshold", 94.0, 99.0),
        ("z5", "VO2max", 100.0, 110.0),
    )

    @staticmethod
    def calculate_running_pace_zones(threshold_pace_s_per_m: float) -> dict:
        """Pace zones as % of threshold pace (seconds per meter), for running.

        Since pace is time-per-distance (not an output rate like power), the
        convention is inverted from power zones: >100% of threshold pace is
        SLOWER (recovery/endurance), <100% is FASTER (VO2max/speed) — this
        mirrors standard Daniels/Pfitzinger threshold-relative pace zones.
        """
        zones: dict = {}
        for key, name, min_pct, max_pct in TrainingAnalytics._RUNNING_PACE_ZONE_BOUNDS:
            zones[key] = {
                "name": name,
                "min_pct": min_pct,
                "max_pct": max_pct,
                "min_pace_s_per_m": round(threshold_pace_s_per_m * min_pct / 100, 4),
                "max_pace_s_per_m": (
                    round(threshold_pace_s_per_m * max_pct / 100, 4) if max_pct < 999 else None
                ),
            }
        return zones

    @staticmethod
    def calculate_swim_css_zones(css_pace_s_per_100m: float) -> dict:
        """Pace zones as % of Critical Swim Speed (CSS), seconds per 100m.

        Same inverted convention as running: >100% of CSS pace is slower,
        <100% is faster.
        """
        zones: dict = {}
        for key, name, min_pct, max_pct in TrainingAnalytics._SWIM_CSS_ZONE_BOUNDS:
            zones[key] = {
                "name": name,
                "min_pct": min_pct,
                "max_pct": max_pct,
                "min_pace_s_per_100m": (
                    round(css_pace_s_per_100m * min_pct / 100, 2) if min_pct > 0 else 0.0
                ),
                "max_pace_s_per_100m": (
                    round(css_pace_s_per_100m * max_pct / 100, 2) if max_pct < 999 else None
                ),
            }
        return zones

    @staticmethod
    def calculate_hr_zones(lthr: int) -> dict:
        """HR zones as % of Lactate Threshold Heart Rate (LTHR).

        Used for cross-country skiing, where power meters are rare and
        pace is too terrain/snow-dependent to standardize — the standard
        practical fallback is heart rate (Joe Friel / TrainingPeaks model).
        """
        zones: dict = {}
        for key, name, min_pct, max_pct in TrainingAnalytics._HR_ZONE_BOUNDS:
            zones[key] = {
                "name": name,
                "min_pct": min_pct,
                "max_pct": max_pct,
                "min_bpm": round(lthr * min_pct / 100),
                "max_bpm": round(lthr * max_pct / 100),
            }
        return zones
