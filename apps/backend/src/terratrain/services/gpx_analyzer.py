"""GPX track analysis using gpxpy and Polars.

Detects climb segments, computes VAM, and builds a terrain profile
suitable for injection into the coaching agent's system prompt.
"""

from __future__ import annotations

import math

import gpxpy
import gpxpy.gpx
import polars as pl


class GpxAnalyzer:
    # Climb detection thresholds
    MIN_GRADE_PCT = 3.0  # minimum gradient to start a climb
    MIN_CLIMB_LENGTH_M = 300  # minimum sustained length
    HYSTERESIS_M = 50  # how far below threshold before climb ends

    # Downhill detection thresholds
    MIN_DOWNHILL_GRADE_PCT = -2.0  # minimum negative gradient to start a downhill segment
    MIN_DOWNHILL_LENGTH_M = 200  # minimum sustained descent length
    MIN_ELEVATION_LOSS_M = 15.0  # minimum elevation loss

    @staticmethod
    def analyze(gpx_xml: str) -> dict:
        """Parse GPX XML and return a dict matching Route ORM fields."""
        gpx = gpxpy.parse(gpx_xml)

        points: list[dict] = []
        for track in gpx.tracks:
            for segment in track.segments:
                for pt in segment.points:
                    points.append(
                        {
                            "lat": pt.latitude,
                            "lon": pt.longitude,
                            "ele": pt.elevation or 0.0,
                        }
                    )

        if len(points) < 2:
            return GpxAnalyzer._empty_result()

        df = pl.DataFrame(points)
        
        # Smooth elevation data using a rolling mean to eliminate high-frequency GPS noise/jitter.
        # Using a centered window of 5 points, with min_periods=1 to support edges.
        df = df.with_columns(
            pl.col("ele").rolling_mean(window_size=5, min_periods=1, center=True).alias("ele")
        )
        
        df = GpxAnalyzer._compute_distances(df)
        df = GpxAnalyzer._compute_grades(df)

        distance_m = float(df["cumulative_m"].tail(1)[0])
        gain = float(df.filter(pl.col("delta_ele") > 0)["delta_ele"].sum())
        loss = float(df.filter(pl.col("delta_ele") < 0)["delta_ele"].abs().sum())
        climbs = GpxAnalyzer._detect_climbs(df)
        downhills = GpxAnalyzer._detect_downhills(df)
        terrain_score = GpxAnalyzer._compute_terrain_score(gain, distance_m, climbs)

        # Downsample points for lightweight map rendering (max 300 points)
        step = max(1, len(df) // 300)
        sample_rows = df.gather_every(step).to_dicts()
        track_points = [
            {
                "lat": round(float(r["lat"]), 6),
                "lon": round(float(r["lon"]), 6),
                "ele": round(float(r["ele"]), 1),
                "km": round(float(r["cumulative_m"]) / 1000.0, 3),
            }
            for r in sample_rows
        ]

        return {
            "distance_m": distance_m,
            "elevation_gain_m": gain,
            "elevation_loss_m": loss,
            "max_elevation_m": float(df["ele"].max()),
            "min_elevation_m": float(df["ele"].min()),
            "climb_profile": climbs,
            "downhill_profile": downhills,
            "terrain_score": terrain_score,
            "analysis": {
                "point_count": len(points),
                "avg_grade_pct": float(df["grade_pct"].abs().mean()) if distance_m > 0 else 0.0,
                "distance_km": round(distance_m / 1000, 2),
                "elevation_gain_m": round(gain, 1),
                "elevation_loss_m": round(loss, 1),
                "climb_count": len(climbs),
                "downhill_count": len(downhills),
                "downhill_profile": downhills,
                "track_points": track_points,
            },
        }

    @staticmethod
    def _compute_distances(df: pl.DataFrame) -> pl.DataFrame:
        lats = df["lat"].to_list()
        lons = df["lon"].to_list()
        eles = df["ele"].to_list()

        deltas_m = [0.0]
        delta_eles = [0.0]
        for i in range(1, len(lats)):
            d = GpxAnalyzer._haversine(lats[i - 1], lons[i - 1], lats[i], lons[i])
            deltas_m.append(d)
            delta_eles.append(eles[i] - eles[i - 1])

        cumulative = [0.0]
        for d in deltas_m[1:]:
            cumulative.append(cumulative[-1] + d)

        return df.with_columns(
            [
                pl.Series("delta_m", deltas_m),
                pl.Series("delta_ele", delta_eles),
                pl.Series("cumulative_m", cumulative),
            ]
        )

    @staticmethod
    def _compute_grades(df: pl.DataFrame) -> pl.DataFrame:
        grades = []
        for delta_ele, delta_m in zip(df["delta_ele"].to_list(), df["delta_m"].to_list()):
            if delta_m > 0.5:
                grades.append((delta_ele / delta_m) * 100)
            else:
                grades.append(0.0)
        return df.with_columns(pl.Series("grade_pct", grades))

    @staticmethod
    def _detect_climbs(df: pl.DataFrame) -> list[dict]:
        grades = df["grade_pct"].to_list()
        cumulative = df["cumulative_m"].to_list()
        eles = df["ele"].to_list()

        climbs: list[dict] = []
        in_climb = False
        start_idx = 0
        below_threshold_m = 0.0

        for i in range(1, len(grades)):
            grade = grades[i]
            segment_len = cumulative[i] - cumulative[i - 1]

            if not in_climb:
                if grade >= GpxAnalyzer.MIN_GRADE_PCT:
                    in_climb = True
                    start_idx = i
                    below_threshold_m = 0.0
            else:
                if grade < GpxAnalyzer.MIN_GRADE_PCT:
                    below_threshold_m += segment_len
                    if below_threshold_m >= GpxAnalyzer.HYSTERESIS_M:
                        end_idx = i
                        climb = GpxAnalyzer._build_climb(df, start_idx, end_idx, cumulative, eles)
                        if climb["length_m"] >= GpxAnalyzer.MIN_CLIMB_LENGTH_M:
                            climbs.append(climb)
                        in_climb = False
                else:
                    below_threshold_m = 0.0

        if in_climb:
            climb = GpxAnalyzer._build_climb(df, start_idx, len(grades) - 1, cumulative, eles)
            if climb["length_m"] >= GpxAnalyzer.MIN_CLIMB_LENGTH_M:
                climbs.append(climb)

        return climbs

    @staticmethod
    def _build_climb(
        df: pl.DataFrame,
        start_idx: int,
        end_idx: int,
        cumulative: list[float],
        eles: list[float],
    ) -> dict:
        length_m = cumulative[end_idx] - cumulative[start_idx]
        ele_gain = max(0.0, eles[end_idx] - eles[start_idx])
        avg_grade = (ele_gain / length_m * 100) if length_m > 0 else 0.0

        grades_slice = df["grade_pct"].slice(start_idx, end_idx - start_idx).to_list()
        max_grade = max(grades_slice) if grades_slice else 0.0

        vam = None
        if ele_gain > 20:
            avg_speed_kmh = 15.0
            time_h = (length_m / 1000) / avg_speed_kmh
            vam = ele_gain / time_h if time_h > 0 else None

        return {
            "start_km": round(cumulative[start_idx] / 1000, 2),
            "end_km": round(cumulative[end_idx] / 1000, 2),
            "length_m": round(length_m, 0),
            "elevation_gain_m": round(ele_gain, 1),
            "avg_grade_pct": round(avg_grade, 1),
            "max_grade_pct": round(max_grade, 1),
            "vam": round(vam) if vam else None,
            "category": GpxAnalyzer._classify_climb(ele_gain, avg_grade),
        }

    @staticmethod
    def _classify_climb(ele_gain_m: float, avg_grade_pct: float) -> str | None:
        score = ele_gain_m * avg_grade_pct
        if score >= 8000:
            return "hc"
        elif score >= 6400:
            return "cat1"
        elif score >= 3200:
            return "cat2"
        elif score >= 1600:
            return "cat3"
        elif score >= 800:
            return "cat4"
        return None

    @staticmethod
    def _compute_terrain_score(gain_m: float, distance_m: float, climbs: list[dict]) -> float:
        """0–1 composite terrain complexity score."""
        if distance_m == 0:
            return 0.0
        gain_per_km = gain_m / (distance_m / 1000)
        grade_score = min(1.0, gain_per_km / 30.0)
        climb_score = min(1.0, len(climbs) / 5.0)
        return round((grade_score * 0.6 + climb_score * 0.4), 3)

    @staticmethod
    def _haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        R = 6371000.0
        phi1, phi2 = math.radians(lat1), math.radians(lat2)
        dphi = math.radians(lat2 - lat1)
        dlambda = math.radians(lon2 - lon1)
        a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
        return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    @staticmethod
    def _detect_downhills(df: pl.DataFrame) -> list[dict]:
        grades = df["grade_pct"].to_list()
        cumulative = df["cumulative_m"].to_list()
        eles = df["ele"].to_list()

        downhills: list[dict] = []
        in_downhill = False
        start_idx = 0
        above_threshold_m = 0.0

        for i in range(1, len(grades)):
            grade = grades[i]
            segment_len = cumulative[i] - cumulative[i - 1]

            if not in_downhill:
                if grade <= GpxAnalyzer.MIN_DOWNHILL_GRADE_PCT:
                    in_downhill = True
                    start_idx = i
                    above_threshold_m = 0.0
            else:
                if grade > GpxAnalyzer.MIN_DOWNHILL_GRADE_PCT:
                    above_threshold_m += segment_len
                    if above_threshold_m >= GpxAnalyzer.HYSTERESIS_M:
                        end_idx = i
                        downhill = GpxAnalyzer._build_downhill(df, start_idx, end_idx, cumulative, eles)
                        if (
                            downhill["length_m"] >= GpxAnalyzer.MIN_DOWNHILL_LENGTH_M
                            and downhill["elevation_loss_m"] >= GpxAnalyzer.MIN_ELEVATION_LOSS_M
                        ):
                            downhills.append(downhill)
                        in_downhill = False
                else:
                    above_threshold_m = 0.0

        if in_downhill:
            downhill = GpxAnalyzer._build_downhill(df, start_idx, len(grades) - 1, cumulative, eles)
            if (
                downhill["length_m"] >= GpxAnalyzer.MIN_DOWNHILL_LENGTH_M
                and downhill["elevation_loss_m"] >= GpxAnalyzer.MIN_ELEVATION_LOSS_M
            ):
                downhills.append(downhill)

        return downhills

    @staticmethod
    def _build_downhill(
        df: pl.DataFrame,
        start_idx: int,
        end_idx: int,
        cumulative: list[float],
        eles: list[float],
    ) -> dict:
        length_m = cumulative[end_idx] - cumulative[start_idx]
        ele_loss = max(0.0, eles[start_idx] - eles[end_idx])
        avg_grade = (-ele_loss / length_m * 100) if length_m > 0 else 0.0

        grades_slice = df["grade_pct"].slice(start_idx, end_idx - start_idx).to_list()
        min_grade = min(grades_slice) if grades_slice else 0.0

        return {
            "start_km": round(cumulative[start_idx] / 1000, 2),
            "end_km": round(cumulative[end_idx] / 1000, 2),
            "length_m": round(length_m, 0),
            "elevation_loss_m": round(ele_loss, 1),
            "avg_grade_pct": round(avg_grade, 1),
            "min_grade_pct": round(min_grade, 1),
        }

    @staticmethod
    def _empty_result() -> dict:
        return {
            "distance_m": 0.0,
            "elevation_gain_m": 0.0,
            "elevation_loss_m": 0.0,
            "max_elevation_m": None,
            "min_elevation_m": None,
            "climb_profile": [],
            "downhill_profile": [],
            "terrain_score": 0.0,
            "analysis": {},
        }
