import json
from datetime import date, datetime, timedelta, timezone
from typing import Any, AsyncGenerator

import httpx
import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from terratrain.config import get_settings
from terratrain.constants import Sport
from terratrain.db.models.athlete import Athlete
from terratrain.db.models.route import Route
from terratrain.db.models.weekly_plan import WeeklyPlan
from terratrain.db.models.workout import Workout
from terratrain.schemas.weekly_plan import WeeklyPlanCreateRequest
from terratrain.schemas.workout import StrengthExercise, WorkoutPhase, WorkoutPlan
from terratrain.services.coaching_agent import CoachingAgent, OllamaError
from terratrain.services.fitness_service import get_fitness
from terratrain.services.mesocycle_detector import MesocycleDetector
from terratrain.services.workout_formatter import WorkoutFormatter

logger = structlog.get_logger()

WEEKLY_PLAN_TOOL_SCHEMA = {
    "type": "object",
    "properties": {
        "coach_rationale": {
            "type": "string",
            "description": "The weekly periodisation rationale for this week based on the mesocycle status and training stress.",
        },
        "daily_workouts": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "day_of_week": {
                        "type": "integer",
                        "description": "0 for Monday, 1 for Tuesday, ..., 6 for Sunday",
                    },
                    "name": {"type": "string", "description": "The name of the workout."},
                    "workout_type": {
                        "type": "string",
                        "enum": ["endurance", "tempo", "threshold", "vo2max", "recovery", "race_simulation"],
                        "description": "The primary focus of this workout.",
                    },
                    "sport": {
                        "type": "string",
                        "enum": [s.value for s in Sport],
                        "description": "The sport of the workout.",
                    },
                    "target_tss": {
                        "type": "number",
                        "description": "Estimated target TSS for this workout.",
                    },
                    "rationale": {
                        "type": "string",
                        "description": "Why the coach prescribed this specific session on this day.",
                    },
                    "coach_notes": {
                        "type": "string",
                        "default": "",
                        "description": "Optional notes/instructions for the athlete.",
                    },
                    "phases": {
                        "type": "array",
                        "description": (
                            "Endurance sports only (cycling/running/swimming/"
                            "cross_country_skiing) — step-by-step phases of the workout."
                        ),
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string", "description": "Phase name (Warmup, Interval, Recovery, Cooldown, etc.)"},
                                "duration_min": {"type": "number", "description": "Duration of this phase in minutes."},
                                "zone": {
                                    "type": "string",
                                    "enum": ["Z1", "Z2", "Z3", "Z4", "Z5", "Z6", "Z7"],
                                    "description": "The target relative-intensity zone (Z1-Z5 for non-cycling sports).",
                                },
                                "target_power_pct": {
                                    "type": "number",
                                    "description": "Cycling only — exact target power as percentage of FTP (e.g. 65). Must be a number, not a string.",
                                },
                                "target_hr_zone": {
                                    "type": "string",
                                    "description": "Optional target HR bpm range like '130-145' or a single bpm value like '140'.",
                                },
                                "target_cadence_rpm": {
                                    "type": "integer",
                                    "description": "Cycling only — optional target cadence in rpm (e.g. 90, 95, 100).",
                                },
                                "description": {"type": "string", "default": "", "description": "Instructions for this phase."},
                                "repeat": {
                                    "type": "integer",
                                    "default": 1,
                                    "description": "Multiplier if this phase is repeated in a block.",
                                },
                            },
                            "required": ["name", "duration_min", "zone"],
                        },
                    },
                    "exercises": {
                        "type": "array",
                        "description": "weight_training only — one entry per exercise.",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string"},
                                "sets": {"type": "integer"},
                                "reps": {"type": "integer"},
                                "rpe": {"type": "number", "description": "1-10 scale, 10 = failure."},
                                "rest_seconds": {"type": "integer"},
                                "description": {"type": "string"},
                            },
                            "required": ["name", "sets", "reps"],
                        },
                    },
                },
                "required": ["day_of_week", "name", "workout_type", "sport", "target_tss", "rationale"],
            },
        },
    },
    "required": ["coach_rationale", "daily_workouts"],
}

WEEK_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "query_training_science",
            "description": "Search the local training science database for peer-reviewed studies.",
            "parameters": {
                "type": "object",
                "properties": {
                    "topic": {"type": "string", "description": "e.g. sweet spot training, recovery cycle duration"}
                },
                "required": ["topic"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "calculate_zones",
            "description": "Compute training zones based on FTP.",
            "parameters": {
                "type": "object",
                "properties": {
                    "ftp": {"type": "integer", "description": "Athlete Functional Threshold Power in Watts"},
                    "model": {"type": "string", "default": "coggan_classic"},
                },
                "required": ["ftp"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "calculate_running_pace_zones",
            "description": "Return running pace zone boundaries relative to threshold pace.",
            "parameters": {
                "type": "object",
                "properties": {"threshold_pace_s_per_m": {"type": "number"}},
                "required": ["threshold_pace_s_per_m"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "calculate_swim_css_zones",
            "description": "Return swim pace zone boundaries relative to Critical Swim Speed.",
            "parameters": {
                "type": "object",
                "properties": {"css_pace_s_per_100m": {"type": "number"}},
                "required": ["css_pace_s_per_100m"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "calculate_hr_zones",
            "description": "Return HR zone boundaries relative to LTHR (used for cross_country_skiing).",
            "parameters": {
                "type": "object",
                "properties": {"lthr": {"type": "integer"}},
                "required": ["lthr"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "estimate_tss",
            "description": "Calculate estimated TSS from duration and intensity factor.",
            "parameters": {
                "type": "object",
                "properties": {
                    "duration_min": {"type": "number"},
                    "intensity_factor": {"type": "number", "description": "e.g. 0.72 for zone 2, 0.95 for threshold"},
                },
                "required": ["duration_min", "intensity_factor"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "final_answer",
            "description": "Submit the completed weekly training plan. Call this when ready.",
            "parameters": WEEKLY_PLAN_TOOL_SCHEMA,
        },
    },
]


from terratrain.services.workout_normalizer import normalize_workout_duration


class WeeklyCoachingAgent(CoachingAgent):

    async def generate_week(
        self, athlete: Athlete, body: WeeklyPlanCreateRequest
    ) -> AsyncGenerator[dict[str, Any], None]:
        yield {"event": "thinking", "data": "Gathering athlete context..."}

        # 1. Fetch PMC and history
        pmc = await self._get_pmc(athlete)
        det_result = await MesocycleDetector.get_tss_history_and_recommendation(
            athlete=athlete,
            session=self._session,
            start_date=body.start_date,
            mesocycle_type=body.mesocycle_type,
        )

        # 2. Map routes for schedules
        schedules_context = []
        for sched in body.schedules:
            sc_data: dict[str, Any] = {
                "day_of_week": sched.day_of_week,
                "duration_min": sched.duration_min,
                "sport": sched.sport or athlete.sport,
                "notes": sched.notes,
            }
            if sched.route_id:
                route = await self._session.get(Route, sched.route_id)
                if route:
                    sc_data["route"] = {
                        "name": route.name,
                        "distance_km": round(route.distance_m / 1000, 1),
                        "elevation_gain_m": round(route.elevation_gain_m, 0),
                        "max_elevation_m": round(route.max_elevation_m, 0) if route.max_elevation_m else None,
                        "terrain_score": route.terrain_score,
                        "climbs": route.climb_profile[:6] if route.climb_profile else [],
                    }
            schedules_context.append(sc_data)

        # 3. Build prompts
        ctx = {
            "athlete": {
                "name": athlete.name,
                "sport": athlete.sport,
                "ftp_watts": athlete.ftp_watts,
                "threshold_pace_s_per_m": athlete.threshold_pace_s_per_m,
                "css_pace_s_per_100m": athlete.css_pace_s_per_100m,
                "weight_kg": athlete.weight_kg,
                "lthr": athlete.lthr,
            },
            "pmc": pmc,
            "history": det_result["history"],
            "week_type": body.week_type,
            "mesocycle_type": body.mesocycle_type,
            "aggressiveness": body.aggressiveness,
            "notes": body.notes,
            "schedules": schedules_context,
        }

        system_prompt = self._build_weekly_system_prompt(ctx)
        llm_provider = body.provider or self._settings.resolved_llm_provider

        yield {"event": "thinking", "data": "Starting weekly coaching agent loop..."}

        messages: list[dict] = [{"role": "user", "content": system_prompt}]
        plan_data: dict | None = None
        validation_retries_left = 1
        max_turns = self._settings.ollama_max_agent_turns + 2

        for turn in range(max_turns):
            yield {"event": "thinking", "data": f"Agent turn {turn + 1}..."}

            try:
                response = await self._weekly_call_llm(messages, llm_provider)
            except OllamaError as exc:
                yield {"event": "error", "data": str(exc)}
                return

            assistant_msg = response.get("message", {})
            messages.append(assistant_msg)
            logger.info("Coaching agent turn response", turn=turn+1, assistant_msg=assistant_msg)

            tool_calls = assistant_msg.get("tool_calls", [])
            if not tool_calls:
                yield {"event": "thinking", "data": assistant_msg.get("content", "")}
                continue

            for tc in tool_calls:
                fn_name = tc.get("function", {}).get("name", "")
                fn_args = tc.get("function", {}).get("arguments", {})

                yield {"event": "tool_call", "data": f"{fn_name}({json.dumps(fn_args)[:120]})"}

                if fn_name == "final_answer":
                    plan_data = fn_args
                    break

                result = await self._execute_tool(fn_name, fn_args)
                yield {"event": "tool_result", "data": f"{fn_name} → {str(result)[:200]}"}

            if plan_data is None:
                continue

            # Validate each daily workout generated
            validation_errors = []
            for d_spec in plan_data.get("daily_workouts", []):
                try:
                    candidate = WorkoutPlan(
                        name=d_spec["name"],
                        workout_type=d_spec["workout_type"],
                        sport=d_spec.get("sport", athlete.sport),
                        phases=[WorkoutPhase(**p) for p in d_spec.get("phases", [])],
                        exercises=[StrengthExercise(**e) for e in d_spec.get("exercises", [])],
                        target_tss=d_spec.get("target_tss", 0),
                        rationale=d_spec["rationale"],
                        coach_notes=d_spec.get("coach_notes", ""),
                    )
                    errs = WorkoutFormatter.validate(candidate)
                    if errs:
                        day_label = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"][
                            d_spec["day_of_week"]
                        ]
                        validation_errors.extend(
                            [f"Day {day_label} ({candidate.name}): {e}" for e in errs]
                        )
                except Exception as exc:
                    validation_errors.append(
                        f"Day Spec for day index {d_spec.get('day_of_week')} failed schema checks: {exc}"
                    )

            if not validation_errors:
                break

            if validation_retries_left > 0:
                validation_retries_left -= 1
                feedback = (
                    "Your weekly plan was REJECTED by the validator. Problems:\n- "
                    + "\n- ".join(validation_errors)
                    + "\nFix these issues and call final_answer again with a corrected plan."
                )
                yield {
                    "event": "thinking",
                    "data": f"Weekly plan rejected ({len(validation_errors)} issue(s)) — asking coach to revise...",
                }
                final_answer_id = None
                for tc in tool_calls:
                    if tc.get("function", {}).get("name") == "final_answer":
                        final_answer_id = tc.get("id")
                        break
                tool_msg = {
                    "role": "tool",
                    "content": feedback,
                    "name": "final_answer",
                }
                if final_answer_id:
                    tool_msg["tool_call_id"] = final_answer_id
                messages.append(tool_msg)
                plan_data = None
                continue

                if fn_name == "final_answer":
                    plan_data = fn_args
                    break

            if plan_data is not None:
                break

        if plan_data is None:
            yield {"event": "error", "data": "Agent did not produce a valid weekly plan"}
            return

        # 4. Save WeeklyPlan and its Workouts
        yield {"event": "thinking", "data": "Saving weekly plan..."}

        weekly_plan = WeeklyPlan(
            athlete_id=athlete.id,
            start_date=body.start_date,
            mesocycle_type=body.mesocycle_type,
            week_type=body.week_type,
            coach_rationale=plan_data.get("coach_rationale"),
            notes=body.notes,
        )
        self._session.add(weekly_plan)
        await self._session.commit()
        await self._session.refresh(weekly_plan)

        # Group body.schedules by day_of_week for multi-session support
        from collections import defaultdict
        schedules_by_day: dict[int, list] = defaultdict(list)
        for sched in body.schedules:
            schedules_by_day[sched.day_of_week].append(sched)

        day_workout_counters: dict[int, int] = defaultdict(int)

        for d_spec in plan_data.get("daily_workouts", []):
            dow = d_spec["day_of_week"]

            # Match N-th workout on this day_of_week to N-th schedule item
            matched_sched = None
            day_schedules = schedules_by_day.get(dow, [])
            idx = day_workout_counters[dow]
            if idx < len(day_schedules):
                matched_sched = day_schedules[idx]
            elif day_schedules:
                matched_sched = day_schedules[-1]

            day_workout_counters[dow] += 1

            sched_sport = matched_sched.sport if matched_sched and matched_sched.sport else None
            effective_sport = d_spec.get("sport") or sched_sport or athlete.sport

            candidate = WorkoutPlan(
                name=d_spec["name"],
                workout_type=d_spec["workout_type"],
                sport=effective_sport,
                phases=[WorkoutPhase(**p) for p in d_spec.get("phases", [])],
                exercises=[StrengthExercise(**e) for e in d_spec.get("exercises", [])],
                target_tss=d_spec.get("target_tss", 0),
                rationale=d_spec["rationale"],
                coach_notes=d_spec.get("coach_notes", ""),
            )

            target_dur = float(matched_sched.duration_min) if matched_sched and matched_sched.duration_min else 0.0
            matched_route_id = matched_sched.route_id if matched_sched else None

            if target_dur > 0 and candidate.sport != Sport.WEIGHT_TRAINING:
                candidate = normalize_workout_duration(candidate, target_dur)

            structured_text = WorkoutFormatter.to_intervals_icu(candidate, athlete=athlete)
            structured_text = WorkoutFormatter.apply_press_lap(structured_text, body.press_lap)

            # weight_training candidates have no `phases` (they use `exercises`,
            # which carry no per-set duration estimate) — duration is unknown.
            duration_seconds = None
            if candidate.sport != Sport.WEIGHT_TRAINING:
                total_min = sum(p.duration_min * max(1, p.repeat) for p in candidate.phases)
                duration_seconds = int(total_min * 60)

            workout_date = body.start_date + timedelta(days=d_spec["day_of_week"])
            workout = Workout(
                athlete_id=athlete.id,
                weekly_plan_id=weekly_plan.id,
                route_id=matched_route_id,
                name=candidate.name,
                sport=candidate.sport,
                workout_type=candidate.workout_type,
                scheduled_date=workout_date,
                duration_seconds=duration_seconds,
                target_tss=candidate.target_tss,
                structured_text=structured_text,
                press_lap=body.press_lap,
                llm_plan=candidate.model_dump(),
                llm_reasoning=candidate.rationale,
                coach_notes=candidate.coach_notes,
                status="draft",
            )
            self._session.add(workout)

        await self._session.commit()

        # Reload weekly plan with workouts
        await self._session.refresh(weekly_plan)

        yield {
            "event": "weekly_plan",
            "data": {
                "weekly_plan_id": str(weekly_plan.id),
                "mesocycle_type": weekly_plan.mesocycle_type,
                "week_type": weekly_plan.week_type,
                "coach_rationale": weekly_plan.coach_rationale,
            },
        }

    def _build_weekly_system_prompt(self, ctx: dict) -> str:
        athlete = ctx["athlete"]
        pmc = ctx["pmc"]
        history = ctx["history"]
        week_type = ctx["week_type"]
        mesocycle_type = ctx["mesocycle_type"]
        notes = ctx["notes"]
        schedules = ctx["schedules"]

        schedule_text = ""
        day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        for s in schedules:
            day_name = day_names[s["day_of_week"]]
            route_text = ""
            if "route" in s:
                r = s["route"]
                ele_text = f", max ele {r['max_elevation_m']}m" if r.get("max_elevation_m") else ""
                route_text = f", Route: {r['name']} ({r['distance_km']} km, {r['elevation_gain_m']} m elevation{ele_text}, terrain score {r['terrain_score']})"
                if r.get("climbs"):
                    route_text += "\n    Route Topography & Key Climbs:\n"
                    # Average speed assumed ~23 km/h for endurance/warmup timing estimation
                    for c in r["climbs"]:
                        start_km = c.get("start_km", 0.0)
                        end_km = c.get("end_km", 0.0)
                        start_min = round(start_km * (60.0 / 23.0))
                        end_min = round(end_km * (60.0 / 23.0))
                        cat_str = f" ({c['category']})" if c.get("category") else ""
                        route_text += (
                            f"      * Climb: km {start_km:.1f} to {end_km:.1f} "
                            f"(ESTIMATED RIDE WINDOW: min {start_min} to min {end_min}), "
                            f"gain: {c.get('elevation_gain_m', 0):.0f}m, avg grade: {c.get('avg_grade_pct', 0):.1f}%{cat_str}\n"
                        )

            sched_sport_str = f" ({s['sport']})" if s.get("sport") else ""
            schedule_text += f"  - {day_name}{sched_sport_str}: {s['duration_min']:.0f} min target duration{route_text}\n"
            if s.get("notes"):
                schedule_text += f"    Notes for this day: {s['notes']}\n"

        history_text = "\n".join(
            f"  - {h['week_label']}: {h['tss']:.0f} TSS" for h in history
        )

        sport = athlete["sport"]
        # Inject a "day_of_week" line into the shared single-workout example
        # (daily_workouts items need it; the shared block doesn't include it).
        example_lines = self._sport_example_block(sport).split("\n")
        example_lines.insert(1, '      "day_of_week": 1,')
        daily_workout_example = "\n".join(example_lines)

        aggressiveness = ctx.get("aggressiveness", 0)
        if aggressiveness > 0:
            agg_guide = f"HIGHER / AGGRESSIVE (+{aggressiveness}): Increase overall weekly TSS targets (+15% to +30%), prescribe higher interval volumes and push progressive overloading aggressively."
        elif aggressiveness < 0:
            agg_guide = f"LOWER / CONSERVATIVE ({aggressiveness}): Reduce overall weekly TSS targets (-15% to -30%), keep workout durations/intensities conservative to prioritize recovery and freshness."
        else:
            agg_guide = "BALANCED / STANDARD (0): Standard baseline weekly periodization TSS targets matching current mesocycle recommendations."

        prompt = f"""You are TerraTrain, an expert {self._sport_label(sport)} coach.

## Athlete Profile
{self._athlete_profile_block(athlete)}

## Current Training Load
CTL (fitness): {pmc["ctl"]}
ATL (fatigue): {pmc["atl"]}
TSB (form): {pmc["tsb"]}

## Training Stress History (Weekly TSS)
{history_text}

## Periodisation Goal for the Upcoming Week
Mesocycle Type: {mesocycle_type}
Week Type: {week_type}
Training Load Aggressiveness: {agg_guide}

## Athlete's Day-by-Day Request for the Week
{schedule_text}

## Notes & Constraints
{notes or "None"}

## Instructions
Design a cohesive weekly training plan for the athlete. You must generate structured workouts for every day requested by the athlete.
For days not requested by the athlete, do NOT output any workouts for that day (they will be rest days).

1. **Recovery Week Principles**:
   - If the week type is "recovery", all workouts must be active recovery (Z1/Z2) under 75% FTP. Keep TSS low and focus on physiological recovery.
   
2. **Load Week Principles**:
   - Workouts should support progressive overloading (load_1 < load_2 < load_3). 
   - Incorporate structured intervals (Z3/Z4/Z5) depending on the athlete's requested duration and form.
   
3. **Route Integration & Topography Alignment**:
   - If a day includes an assigned route, inspect its key climb timing windows (e.g. "Climb: km 18 to 24.5 / ESTIMATED RIDE WINDOW: min 47 to min 64").
   - High-intensity work (Z4/Z5 intervals, tempo efforts) MUST be executed ON the climbs (between climb start and end time windows).
   - Set Warmup + Aerobic Prep duration so that the high-intensity intervals start exactly when reaching the climb.
   - Descents and post-summit sections MUST be assigned to Z1/Z2 recovery or cooldown.

4. **Hard Rules for every individual workout**:
   - STRICT DURATION MATCHING (endurance sports only): the total duration of all phases in a workout MUST strictly equal the requested duration for that day (e.g. if 105 min is requested, sum of all phase durations MUST equal 105 min). Not applicable to weight_training, which has no continuous duration.
{self._sport_hard_rules_block(sport)}

## IMPORTANT: CALL final_answer IMMEDIATELY
Do not write long text introductions. You must formulate the weekly plan and call the `final_answer` tool with the structured plan.

Here is an example structure of the arguments for calling `final_answer` (one day shown; repeat the `daily_workouts` entry shape for every requested day, adding `"day_of_week"` to each):
{{
  "coach_rationale": "Weekly periodisation rationale explaining the block structure...",
  "daily_workouts": [
    {daily_workout_example}
  ]
}}
"""
        return prompt

    async def _weekly_call_llm(self, messages: list[dict], provider: str) -> dict:
        if provider == "gemini":
            return await self._weekly_call_gemini(messages)
        return await self._weekly_call_ollama(messages)

    async def _weekly_call_ollama(self, messages: list[dict]) -> dict:
        settings = self._settings
        try:
            async with httpx.AsyncClient(timeout=settings.ollama_request_timeout) as client:
                resp = await client.post(
                    f"{settings.ollama_base_url}/api/chat",
                    json={
                        "model": settings.ollama_chat_model,
                        "messages": messages,
                        "tools": WEEK_TOOLS,
                        "stream": False,
                        "options": {"temperature": 0.3},
                    },
                )
        except httpx.HTTPError as exc:
            raise OllamaError(
                f"Could not reach the AI service at {settings.ollama_base_url}. Is Ollama running? ({exc})"
            ) from exc

        if resp.status_code == 404:
            raise OllamaError(
                f"The AI model '{settings.ollama_chat_model}' is not installed."
            )
        if resp.status_code >= 400:
            raise OllamaError(
                f"The AI model returned an error (HTTP {resp.status_code}): {resp.text[:200]}"
            )
        return resp.json()

    async def _weekly_call_gemini(self, messages: list[dict]) -> dict:
        settings = self._settings
        if not settings.gemini_api_key:
            raise OllamaError("GEMINI_API_KEY is not set. Please set it in your .env file.")

        headers = {
            "Authorization": f"Bearer {settings.gemini_api_key}",
            "Content-Type": "application/json",
        }

        formatted_messages = []
        for msg in messages:
            msg_copy = {}
            for k, v in msg.items():
                if k in ("role", "content", "name", "tool_call_id"):
                    msg_copy[k] = v
                elif k == "tool_calls":
                    tool_calls_copy = []
                    for tc in v:
                        fn = tc.get("function", {})
                        args = fn.get("arguments", {})
                        if isinstance(args, dict):
                            args_str = json.dumps(args)
                        elif isinstance(args, str):
                            args_str = args
                        else:
                            args_str = "{}"
                        tc_payload = {
                            "id": tc.get("id"),
                            "type": tc.get("type", "function"),
                            "function": {
                                "name": fn.get("name"),
                                "arguments": args_str
                            }
                        }
                        if "extra_content" in tc:
                            tc_payload["extra_content"] = tc["extra_content"]
                        tool_calls_copy.append(tc_payload)
                    msg_copy["tool_calls"] = tool_calls_copy
            if "content" in msg_copy and msg_copy["content"] is None:
                msg_copy["content"] = ""
            formatted_messages.append(msg_copy)

        # Gemini's OpenAI translation layer has known issues with multi-turn tool interactions.
        # By providing only the final_answer tool, we ensure it generates the complete weekly plan in a single turn.
        gemini_tools = [t for t in WEEK_TOOLS if t["function"]["name"] == "final_answer"]

        payload = {
            "model": settings.gemini_chat_model,
            "messages": formatted_messages,
            "tools": gemini_tools,
            "temperature": 0.3,
        }

        try:
            async with httpx.AsyncClient(timeout=settings.ollama_request_timeout) as client:
                resp = await client.post(
                    f"{settings.gemini_api_base}/chat/completions",
                    headers=headers,
                    json=payload,
                )
        except httpx.HTTPError as exc:
            raise OllamaError(
                f"Could not reach Gemini API at {settings.gemini_api_base}. ({exc})"
            ) from exc

        if resp.status_code >= 400:
            logger.error("gemini.api_error", status_code=resp.status_code, body=resp.text[:500])
            raise OllamaError(
                f"Gemini API returned an error (HTTP {resp.status_code}): {resp.text[:200]}"
            )

        resp_data = resp.json()
        try:
            choice = resp_data["choices"][0]
            logger.info("Gemini raw choice response", choice=choice)
            msg = choice["message"]

            tool_calls = msg.get("tool_calls", [])
            mapped_tool_calls = []
            for tc in tool_calls:
                fn = tc.get("function", {})
                args = fn.get("arguments", {})
                if isinstance(args, str):
                    try:
                        args = json.loads(args)
                    except Exception:
                        args = {}
                mapped_tc = {
                    "id": tc.get("id"),
                    "type": "function",
                    "function": {"name": fn.get("name"), "arguments": args},
                }
                if "extra_content" in tc:
                    mapped_tc["extra_content"] = tc["extra_content"]
                mapped_tool_calls.append(mapped_tc)

            normalized_msg = {
                "role": "assistant",
                "content": msg.get("content") or "",
            }
            if mapped_tool_calls:
                normalized_msg["tool_calls"] = mapped_tool_calls

            return {"message": normalized_msg}
        except Exception as exc:
            raise OllamaError(f"Failed to parse Gemini API response: {exc}") from exc
