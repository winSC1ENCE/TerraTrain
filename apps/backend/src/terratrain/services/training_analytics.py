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

        daily_tss = (
            df.group_by("date")
            .agg(pl.col("tss").sum().alias("tss"))
            .sort("date")
        )

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
        return round((duration_min / 60) * (intensity_factor ** 2) * 100, 1)

    @staticmethod
    def calculate_zones(ftp: int, model: str = "coggan_classic") -> dict:
        """Return power zone boundaries as percentage of FTP."""
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
