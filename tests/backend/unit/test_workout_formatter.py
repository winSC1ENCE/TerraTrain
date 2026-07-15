"""Unit tests for WorkoutFormatter."""

import pytest

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
    plan = make_plan([
        {"name": "Warmup", "duration_min": 15, "zone": "Z2", "target_power_pct": 65},
        {"name": "Threshold", "duration_min": 20, "zone": "Z4", "target_power_pct": 95},
        {"name": "Cooldown", "duration_min": 10, "zone": "Z1", "target_power_pct": 50},
    ])
    text = WorkoutFormatter.to_intervals_icu(plan)
    assert "@65%FTP" in text
    assert "@95%FTP" in text
    assert "@50%FTP" in text


def test_repeat_block_formatted_correctly():
    plan = make_plan([
        {"name": "Warmup", "duration_min": 15, "zone": "Z2", "target_power_pct": 65, "repeat": 1},
        {"name": "On", "duration_min": 4, "zone": "Z5", "target_power_pct": 110, "repeat": 5},
        {"name": "Off", "duration_min": 2, "zone": "Z1", "target_power_pct": 50, "repeat": 5},
        {"name": "Cooldown", "duration_min": 10, "zone": "Z1", "target_power_pct": 55, "repeat": 1},
    ])
    text = WorkoutFormatter.to_intervals_icu(plan)
    assert "5x(" in text


def test_validation_too_short():
    plan = make_plan([
        {"name": "Sprint", "duration_min": 1, "zone": "Z5", "target_power_pct": 150},
    ], target_tss=10)
    errors = WorkoutFormatter.validate(plan)
    assert any("duration" in e.lower() for e in errors)


def test_validation_passes_for_valid_plan():
    plan = make_plan([
        {"name": "Warmup", "duration_min": 15, "zone": "Z2", "target_power_pct": 65},
        {"name": "Main", "duration_min": 30, "zone": "Z4", "target_power_pct": 90},
        {"name": "Cooldown", "duration_min": 10, "zone": "Z1", "target_power_pct": 50},
    ])
    errors = WorkoutFormatter.validate(plan)
    assert errors == []


def test_hr_target_uses_bpm():
    plan = make_plan([
        {"name": "Endurance", "duration_min": 60, "zone": "Z2", "target_hr_zone": "130-145"},
    ])
    text = WorkoutFormatter.to_intervals_icu(plan)
    assert "bpm" in text
