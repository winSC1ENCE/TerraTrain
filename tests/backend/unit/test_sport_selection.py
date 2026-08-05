"""Unit tests for per-workout / per-request sport selection."""

import pytest
from terratrain.schemas.coaching import CoachingRequest
from terratrain.schemas.weekly_plan import DailyScheduleInput
from terratrain.constants import Sport


def test_coaching_request_accepts_valid_sport():
    req = CoachingRequest(workout_type="threshold", sport="running")
    assert req.sport == Sport.RUNNING


def test_coaching_request_rejects_invalid_sport():
    with pytest.raises(Exception):
        CoachingRequest(workout_type="threshold", sport="invalid_sport")


def test_daily_schedule_input_accepts_valid_sport():
    item = DailyScheduleInput(day_of_week=0, duration_min=60.0, sport="swimming")
    assert item.sport == Sport.SWIMMING


def test_daily_schedule_input_rejects_invalid_sport():
    with pytest.raises(Exception):
        DailyScheduleInput(day_of_week=0, duration_min=60.0, sport="skateboarding")


def test_coaching_request_aggressiveness_range():
    req_default = CoachingRequest(workout_type="threshold")
    assert req_default.aggressiveness == 0

    req_valid = CoachingRequest(workout_type="threshold", aggressiveness=2)
    assert req_valid.aggressiveness == 2

    with pytest.raises(Exception):
        CoachingRequest(workout_type="threshold", aggressiveness=5)


def test_coaching_request_load_policy_validation():
    req_default = CoachingRequest(workout_type="threshold")
    assert req_default.load_policy == "target"

    req_exceed = CoachingRequest(workout_type="threshold", load_policy="allow_exceed")
    assert req_exceed.load_policy == "allow_exceed"

    req_below = CoachingRequest(workout_type="threshold", load_policy="allow_fall_below")
    assert req_below.load_policy == "allow_fall_below"

    with pytest.raises(Exception):
        CoachingRequest(workout_type="threshold", load_policy="invalid_policy")


