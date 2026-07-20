import pytest
from terratrain.schemas.workout import WorkoutPhase, WorkoutPlan
from terratrain.services.weekly_coaching_agent import WeeklyCoachingAgent

def test_normalize_workout_duration_oversized():
    # Candidate workout is 145 min (20m warmup + 40m prep + 3*(8m work + 8m rec = 48m) + 37m cooldown)
    # Target duration is 105 min.
    candidate = WorkoutPlan(
        name="Test Oversized Workout",
        workout_type="vo2max",
        sport="cycling",
        target_tss=100,
        rationale="Testing duration adjustment",
        coach_notes="",
        phases=[
            WorkoutPhase(name="Warmup", duration_min=20, zone="Z2", target_power_pct=60, repeat=1),
            WorkoutPhase(name="Aerobic Prep", duration_min=40, zone="Z2", target_power_pct=65, repeat=1),
            WorkoutPhase(name="VO2max", duration_min=8, zone="Z5", target_power_pct=108, repeat=3),
            WorkoutPhase(name="Recovery", duration_min=8, zone="Z1", target_power_pct=50, repeat=3),
            WorkoutPhase(name="Cooldown", duration_min=37, zone="Z2", target_power_pct=65, repeat=1),
        ]
    )

    adjusted = WeeklyCoachingAgent._normalize_workout_duration(candidate, 105.0)
    total_min = sum(p.duration_min * max(1, p.repeat) for p in adjusted.phases)
    assert total_min == 105.0

def test_normalize_workout_duration_undersized():
    # Candidate workout is 60 min, target is 90 min.
    candidate = WorkoutPlan(
        name="Test Undersized Workout",
        workout_type="endurance",
        sport="cycling",
        target_tss=60,
        rationale="Testing undersized duration",
        coach_notes="",
        phases=[
            WorkoutPhase(name="Warmup", duration_min=10, zone="Z2", target_power_pct=60, repeat=1),
            WorkoutPhase(name="Endurance", duration_min=40, zone="Z2", target_power_pct=70, repeat=1),
            WorkoutPhase(name="Cooldown", duration_min=10, zone="Z1", target_power_pct=55, repeat=1),
        ]
    )

    adjusted = WeeklyCoachingAgent._normalize_workout_duration(candidate, 90.0)
    total_min = sum(p.duration_min * max(1, p.repeat) for p in candidate.phases)
    assert total_min == 90.0
