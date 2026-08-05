import pytest
from unittest.mock import MagicMock
from terratrain.services.coaching_agent import CoachingAgent

def test_coaching_agent_build_context_with_load_policy_and_weekly_context():
    agent = CoachingAgent(session=MagicMock())
    athlete = MagicMock()
    athlete.name = "Test Athlete"
    athlete.sport = "cycling"
    athlete.ftp_watts = 250
    athlete.threshold_pace_s_per_m = None
    athlete.css_pace_s_per_100m = None
    athlete.weight_kg = 70
    athlete.lthr = 165
    athlete.training_zones = None

    pmc = {"ctl": 50, "atl": 60, "tsb": -10, "weekly_tss": 350}
    rag_chunks = []
    weekly_ctx = {
        "week_type": "load_1",
        "target_tss": 450,
        "start_date": "2026-08-03",
        "other_workouts": [
          {"name": "VO2 Max Intervals", "sport": "cycling", "target_tss": 90}
        ]
    }

    context = agent._build_context(
        athlete=athlete,
        pmc=pmc,
        route=None,
        rag_chunks=rag_chunks,
        workout_type="threshold",
        notes="Testing load policy",
        sport="cycling",
        aggressiveness=1,
        load_policy="allow_exceed",
        weekly_plan_context=weekly_ctx,
    )

    assert context["load_policy"] == "allow_exceed"
    assert context["weekly_plan_context"] == weekly_ctx
    assert context["aggressiveness"] == 1

    prompt = agent._build_system_prompt(context)
    assert "ALLOW EXCEEDING TARGET LOAD" in prompt
    assert "Parent Weekly Plan Context" in prompt
    assert "VO2 Max Intervals" in prompt


def test_coaching_agent_build_context_standalone_session():
    agent = CoachingAgent(session=MagicMock())
    athlete = MagicMock()
    athlete.name = "Standalone Athlete"
    athlete.sport = "running"
    athlete.ftp_watts = None
    athlete.threshold_pace_s_per_m = 240.0
    athlete.css_pace_s_per_100m = None
    athlete.weight_kg = 65
    athlete.lthr = 170
    athlete.training_zones = None

    pmc = {"ctl": 40, "atl": 45, "tsb": -5, "weekly_tss": 200}
    rag_chunks = []

    context = agent._build_context(
        athlete=athlete,
        pmc=pmc,
        route=None,
        rag_chunks=rag_chunks,
        workout_type="tempo",
        notes="Standalone workout test",
        sport="running",
        aggressiveness=0,
        load_policy="target",
        weekly_plan_context=None,
    )

    assert context["load_policy"] == "target"
    assert context["weekly_plan_context"] is None

    prompt = agent._build_system_prompt(context)
    assert "BALANCED / TARGET LOAD" in prompt
    assert "Parent Weekly Plan Context" not in prompt

