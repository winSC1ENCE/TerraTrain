"""Unit tests for WorkoutFormatter."""

from types import SimpleNamespace

from terratrain.schemas.workout import StrengthExercise, WorkoutPhase, WorkoutPlan
from terratrain.services.workout_formatter import WorkoutFormatter


def make_plan(phases: list[dict], sport: str = "cycling", **kwargs) -> WorkoutPlan:
    return WorkoutPlan(
        name="Test Workout",
        workout_type="threshold",
        sport=sport,
        phases=[WorkoutPhase(**p) for p in phases],
        target_tss=kwargs.get("target_tss", 80),
        rationale="Test",
    )


def make_athlete(**overrides) -> SimpleNamespace:
    """A minimal stand-in for the Athlete ORM model — the formatter only
    reads a handful of threshold attributes, so a real DB row isn't needed."""
    defaults = {"threshold_pace_s_per_m": None, "css_pace_s_per_100m": None, "lthr": None}
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def test_simple_warmup_interval_cooldown():
    plan = make_plan(
        [
            {"name": "Warmup", "duration_min": 15, "zone": "Z2", "target_power_pct": 65},
            {"name": "Threshold", "duration_min": 20, "zone": "Z4", "target_power_pct": 95},
            {"name": "Cooldown", "duration_min": 10, "zone": "Z1", "target_power_pct": 50},
        ]
    )
    text = WorkoutFormatter.to_intervals_icu(plan)
    assert "- Warmup 15m 65%" in text
    assert "- Threshold 20m 95%" in text
    assert "- Cooldown 10m 50%" in text


def test_cycling_cadence_formatting():
    plan = make_plan(
        [
            {"name": "Warmup", "duration_min": 15, "zone": "Z2", "target_power_pct": 65, "target_cadence_rpm": 90},
            {"name": "Threshold", "duration_min": 20, "zone": "Z4", "target_power_pct": 100, "target_cadence_rpm": 95},
        ]
    )
    text = WorkoutFormatter.to_intervals_icu(plan)
    assert text == "- Warmup 15m 65% 90rpm\n- Threshold 20m 100% 95rpm"

    text_lap = WorkoutFormatter.apply_press_lap(text, enabled=True)
    assert text_lap == "- Press lap Warmup 15m 65% 90rpm\n- Press lap Threshold 20m 100% 95rpm"


def test_repeat_block_formatted_correctly():
    plan = make_plan(
        [
            {
                "name": "Warmup",
                "duration_min": 15,
                "zone": "Z2",
                "target_power_pct": 65,
                "repeat": 1,
            },
            {"name": "On", "duration_min": 4, "zone": "Z5", "target_power_pct": 110, "repeat": 5},
            {"name": "Off", "duration_min": 2, "zone": "Z1", "target_power_pct": 50, "repeat": 5},
            {
                "name": "Cooldown",
                "duration_min": 10,
                "zone": "Z1",
                "target_power_pct": 55,
                "repeat": 1,
            },
        ]
    )
    text = WorkoutFormatter.to_intervals_icu(plan)
    assert "5x\n- On 4m 110%\n- Off 2m 50%" in text


def test_validation_too_short():
    plan = make_plan(
        [
            {"name": "Sprint", "duration_min": 1, "zone": "Z5", "target_power_pct": 150},
        ],
        target_tss=10,
    )
    errors = WorkoutFormatter.validate(plan)
    assert any("duration" in e.lower() for e in errors)


def test_validation_passes_for_valid_plan():
    plan = make_plan(
        [
            {"name": "Warmup", "duration_min": 15, "zone": "Z2", "target_power_pct": 65},
            {"name": "Main", "duration_min": 30, "zone": "Z4", "target_power_pct": 90},
            {"name": "Cooldown", "duration_min": 10, "zone": "Z1", "target_power_pct": 50},
        ],
        target_tss=55,
    )  # consistent with phases: ~55 implied TSS
    errors = WorkoutFormatter.validate(plan)
    assert errors == []


def test_hr_target_uses_bpm():
    plan = make_plan(
        [
            {"name": "Endurance", "duration_min": 60, "zone": "Z2", "target_hr_zone": "130-145"},
        ]
    )
    text = WorkoutFormatter.to_intervals_icu(plan)
    assert "- Endurance 60m 130-145bpm" in text


def test_hr_zone_label_falls_back_to_power():
    """LLM sometimes writes 'Z2' into target_hr_zone — must NOT render 'Z2bpm'."""
    plan = make_plan(
        [
            {"name": "Warmup", "duration_min": 20, "zone": "Z2", "target_hr_zone": "Z2"},
        ]
    )
    text = WorkoutFormatter.to_intervals_icu(plan)
    assert "Z2bpm" not in text
    assert "- Warmup 20m 65%" in text  # zone fallback


def test_single_hr_value_allowed():
    plan = make_plan(
        [
            {"name": "Steady", "duration_min": 45, "zone": "Z2", "target_hr_zone": "140"},
        ]
    )
    text = WorkoutFormatter.to_intervals_icu(plan)
    assert "- Steady 45m 140bpm" in text


def test_validation_rejects_unrealistic_threshold_interval():
    """4x45min @100% FTP must be rejected (the real-world failure case)."""
    plan = make_plan(
        [
            {"name": "Warmup", "duration_min": 15, "zone": "Z2", "target_power_pct": 65},
            {
                "name": "Main",
                "duration_min": 45,
                "zone": "Z4",
                "target_power_pct": 100,
                "repeat": 4,
            },
            {"name": "Cooldown", "duration_min": 10, "zone": "Z1", "target_power_pct": 50},
        ],
        target_tss=200,
    )
    errors = WorkoutFormatter.validate(plan)
    assert any("30 min or shorter" in e for e in errors)
    assert any("maximum is 60 min" in e for e in errors)


def test_validation_rejects_long_vo2max_interval():
    plan = make_plan(
        [
            {"name": "Warmup", "duration_min": 15, "zone": "Z2", "target_power_pct": 65},
            {"name": "VO2", "duration_min": 12, "zone": "Z5", "target_power_pct": 115},
            {"name": "Cooldown", "duration_min": 10, "zone": "Z1", "target_power_pct": 50},
        ],
        target_tss=60,
    )
    errors = WorkoutFormatter.validate(plan)
    assert any("8 min or shorter" in e for e in errors)


def test_validation_requires_warmup():
    plan = make_plan(
        [
            {"name": "Hard start", "duration_min": 20, "zone": "Z4", "target_power_pct": 95},
            {"name": "Cooldown", "duration_min": 10, "zone": "Z1", "target_power_pct": 50},
        ],
        target_tss=40,
    )
    errors = WorkoutFormatter.validate(plan)
    assert any("warmup" in e.lower() for e in errors)


def test_validation_rejects_inconsistent_tss():
    plan = make_plan(
        [
            {"name": "Warmup", "duration_min": 15, "zone": "Z2", "target_power_pct": 65},
            {"name": "Steady", "duration_min": 40, "zone": "Z2", "target_power_pct": 70},
            {"name": "Cooldown", "duration_min": 10, "zone": "Z1", "target_power_pct": 50},
        ],
        target_tss=150,
    )  # implied ~40 — way off
    errors = WorkoutFormatter.validate(plan)
    assert any("deviates" in e for e in errors)


def test_running_zone_uses_threshold_pace():
    plan = make_plan(
        [{"name": "Tempo", "duration_min": 20, "zone": "Z3", "target_power_pct": None}],
        sport="running",
    )
    athlete = make_athlete(threshold_pace_s_per_m=0.24)  # 4:00/km
    text = WorkoutFormatter.to_intervals_icu(plan, athlete=athlete)
    assert "/km" in text
    assert "%" not in text  # must not fall back to cycling %FTP formatting


def test_running_zone_degrades_gracefully_without_threshold_pace():
    """No threshold pace on file — fall back to a plain zone label, not a bogus pace."""
    plan = make_plan(
        [{"name": "Tempo", "duration_min": 20, "zone": "Z3"}],
        sport="running",
    )
    text = WorkoutFormatter.to_intervals_icu(plan, athlete=make_athlete())
    assert "- Tempo 20m Z3" in text


def test_swim_zone_uses_css_pace():
    plan = make_plan(
        [{"name": "Threshold", "duration_min": 20, "zone": "Z3"}],
        sport="swimming",
    )
    athlete = make_athlete(css_pace_s_per_100m=90.0)
    text = WorkoutFormatter.to_intervals_icu(plan, athlete=athlete)
    assert "/100m" in text


def test_skiing_zone_uses_hr():
    plan = make_plan(
        [{"name": "Endurance", "duration_min": 45, "zone": "Z2"}],
        sport="cross_country_skiing",
    )
    athlete = make_athlete(lthr=165)
    text = WorkoutFormatter.to_intervals_icu(plan, athlete=athlete)
    assert "bpm" in text


def test_weight_training_formats_exercise_lines():
    plan = WorkoutPlan(
        name="Leg Day",
        workout_type="strength",
        sport="weight_training",
        exercises=[
            StrengthExercise(name="Back Squat", sets=4, reps=8, rpe=7),
            StrengthExercise(name="Romanian Deadlift", sets=3, reps=10, rest_seconds=90),
        ],
        target_tss=0,
        rationale="Build posterior chain strength",
    )
    text = WorkoutFormatter.to_intervals_icu(plan)
    assert "- Back Squat 4x8 RPE 7" in text
    assert "- Romanian Deadlift 3x10, rest 90s" in text


def test_weight_training_validation_requires_exercises():
    plan = WorkoutPlan(
        name="Empty",
        workout_type="strength",
        sport="weight_training",
        target_tss=0,
        rationale="Test",
    )
    errors = WorkoutFormatter.validate(plan)
    assert any("no exercises" in e.lower() for e in errors)


def test_weight_training_validation_rejects_bad_rpe():
    plan = WorkoutPlan(
        name="Leg Day",
        workout_type="strength",
        sport="weight_training",
        exercises=[StrengthExercise(name="Bench Press", sets=4, reps=5, rpe=12)],
        target_tss=0,
        rationale="Test",
    )
    errors = WorkoutFormatter.validate(plan)
    assert any("RPE" in e for e in errors)


def test_endurance_validation_uses_relative_intensity_wording_for_non_cycling():
    """Non-cycling endurance validation errors must not say '% FTP'."""
    plan = make_plan(
        [
            {"name": "Hard start", "duration_min": 20, "zone": "Z4", "target_power_pct": 95},
            {"name": "Cooldown", "duration_min": 10, "zone": "Z1", "target_power_pct": 50},
        ],
        sport="running",
        target_tss=40,
    )
    errors = WorkoutFormatter.validate(plan)
    assert any("warmup" in e.lower() for e in errors)
    assert not any("FTP" in e for e in errors)


def test_apply_press_lap_prepends_to_step_lines():
    text = "- Warmup 15m 65%\n- Threshold 20m 95%"
    result = WorkoutFormatter.apply_press_lap(text, enabled=True)
    assert result == "- Press lap Warmup 15m 65%\n- Press lap Threshold 20m 95%"


def test_apply_press_lap_is_idempotent_when_already_present():
    text = "- Press lap Warmup 15m 65%\n- Press lap Threshold 20m 95%"
    result = WorkoutFormatter.apply_press_lap(text, enabled=True)
    assert result == text
    assert result.count("- Press lap ") == 2


def test_apply_press_lap_removes_marker_when_disabled():
    text = "- Press lap Warmup 15m 65%\n- Press lap Threshold 20m 95%"
    result = WorkoutFormatter.apply_press_lap(text, enabled=False)
    assert result == "- Warmup 15m 65%\n- Threshold 20m 95%"


def test_apply_press_lap_disabled_on_text_without_marker_is_noop():
    text = "- Warmup 15m 65%"
    assert WorkoutFormatter.apply_press_lap(text, enabled=False) == text


def test_apply_press_lap_on_empty_text():
    assert WorkoutFormatter.apply_press_lap("", enabled=True) == ""
    assert WorkoutFormatter.apply_press_lap("", enabled=False) == ""
