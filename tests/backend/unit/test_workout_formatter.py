"""Unit tests for WorkoutFormatter."""


from terratrain.schemas.workout import WorkoutPhase, WorkoutPlan
from terratrain.services.workout_formatter import WorkoutFormatter


def make_plan(phases: list[dict], **kwargs) -> WorkoutPlan:
    return WorkoutPlan(
        name="Test Workout",
        workout_type="threshold",
        sport="cycling",
        phases=[WorkoutPhase(**p) for p in phases],
        target_tss=kwargs.get("target_tss", 80),
        rationale="Test",
    )


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
