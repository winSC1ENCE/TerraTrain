import json
from datetime import date, datetime, timedelta, timezone
from typing import Any, AsyncGenerator

import httpx
import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from terratrain.config import get_settings
from terratrain.db.models.athlete import Athlete
from terratrain.db.models.route import Route
from terratrain.db.models.weekly_plan import WeeklyPlan
from terratrain.db.models.workout import Workout
from terratrain.schemas.weekly_plan import WeeklyPlanCreateRequest
from terratrain.schemas.workout import WorkoutPhase, WorkoutPlan
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
                        "enum": ["cycling", "running", "triathlon"],
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
                        "description": "Step-by-step phases of the workout.",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string", "description": "Phase name (Warmup, Interval, Recovery, Cooldown, etc.)"},
                                "duration_min": {"type": "number", "description": "Duration of this phase in minutes."},
                                "zone": {
                                    "type": "string",
                                    "enum": ["Z1", "Z2", "Z3", "Z4", "Z5", "Z6", "Z7"],
                                    "description": "The target Coggan power zone.",
                                },
                                "target_power_pct": {
                                    "type": "number",
                                    "description": "Exact target power as percentage of FTP (e.g. 65). Must be a number, not a string.",
                                },
                                "target_hr_zone": {
                                    "type": "string",
                                    "description": "Optional target HR bpm range like '130-145' or a single bpm value like '140'.",
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
                },
                "required": ["day_of_week", "name", "workout_type", "sport", "target_tss", "rationale", "phases"],
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


class WeeklyCoachingAgent(CoachingAgent):
    async def generate_week(
        self, body: WeeklyPlanCreateRequest
    ) -> AsyncGenerator[dict[str, Any], None]:
        yield {"event": "thinking", "data": "Gathering athlete context..."}

        athlete = await self._session.get(Athlete, body.athlete_id)
        if not athlete:
            yield {"event": "error", "data": "Athlete not found"}
            return

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
                "notes": sched.notes,
            }
            if sched.route_id:
                route = await self._session.get(Route, sched.route_id)
                if route:
                    sc_data["route"] = {
                        "name": route.name,
                        "distance_km": round(route.distance_m / 1000, 1),
                        "elevation_gain_m": round(route.elevation_gain_m, 0),
                        "terrain_score": route.terrain_score,
                    }
            schedules_context.append(sc_data)

        # 3. Build prompts
        ctx = {
            "athlete": {
                "name": athlete.name,
                "sport": athlete.sport,
                "ftp_watts": athlete.ftp_watts,
                "weight_kg": athlete.weight_kg,
                "lthr": athlete.lthr,
            },
            "pmc": pmc,
            "history": det_result["history"],
            "week_type": body.week_type,
            "mesocycle_type": body.mesocycle_type,
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
                        phases=[WorkoutPhase(**p) for p in d_spec["phases"]],
                        target_tss=d_spec["target_tss"],
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

            yield {
                "event": "error",
                "data": "Weekly plan validation failed after retry: " + "; ".join(validation_errors),
            }
            return

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

        for d_spec in plan_data.get("daily_workouts", []):
            candidate = WorkoutPlan(
                name=d_spec["name"],
                workout_type=d_spec["workout_type"],
                sport=d_spec.get("sport", athlete.sport),
                phases=[WorkoutPhase(**p) for p in d_spec["phases"]],
                target_tss=d_spec["target_tss"],
                rationale=d_spec["rationale"],
                coach_notes=d_spec.get("coach_notes", ""),
            )
            structured_text = WorkoutFormatter.to_intervals_icu(candidate)
            total_min = sum(p.duration_min * max(1, p.repeat) for p in candidate.phases)

            # Match route_id from schedule if provided
            matched_route_id = None
            for sched in body.schedules:
                if sched.day_of_week == d_spec["day_of_week"]:
                    matched_route_id = sched.route_id
                    break

            workout_date = body.start_date + timedelta(days=d_spec["day_of_week"])
            workout = Workout(
                athlete_id=athlete.id,
                weekly_plan_id=weekly_plan.id,
                route_id=matched_route_id,
                name=candidate.name,
                sport=candidate.sport,
                workout_type=candidate.workout_type,
                scheduled_date=workout_date,
                duration_seconds=int(total_min * 60),
                target_tss=candidate.target_tss,
                structured_text=structured_text,
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
                route_text = f", Route: {r['name']} ({r['distance_km']} km, {r['elevation_gain_m']} m elevation, terrain score {r['terrain_score']})"
            schedule_text += f"  - {day_name}: {s['duration_min']:.0f} min duration{route_text}\n"
            if s.get("notes"):
                schedule_text += f"    Notes for this day: {s['notes']}\n"

        history_text = "\n".join(
            f"  - {h['week_label']}: {h['tss']:.0f} TSS" for h in history
        )

        prompt = f"""You are TerraTrain, an expert endurance coach specializing in cycling and running.

## Athlete Profile
Name: {athlete["name"]}
Sport: {athlete["sport"]}
FTP: {athlete["ftp_watts"] or "unknown"} W
Weight: {athlete["weight_kg"] or "unknown"} kg
LTHR: {athlete["lthr"] or "unknown"} bpm

## Current Training Load
CTL (fitness): {pmc["ctl"]}
ATL (fatigue): {pmc["atl"]}
TSB (form): {pmc["tsb"]}

## Training Stress History (Weekly TSS)
{history_text}

## Periodisation Goal for the Upcoming Week
Mesocycle Type: {mesocycle_type}
Week Type: {week_type}

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
   
3. **Route Integration**:
   - If a day includes an assigned route, you MUST design the workout to target that route's climbs and profile (e.g. Z4 climbing intervals).

4. **Hard Rules for every individual workout**:
   - First phase of each workout = warmup: at most 75% FTP, at least 10 min
   - Last phase of each workout = cooldown: at most 75% FTP
   - `target_power_pct` must be a NUMBER, never a zone label
   - `target_hr_zone` only as numeric bpm range like "130-145" — NEVER "Z2"
   - Use `repeat` for interval sets (e.g. 4 reps of 5min on / 3min off: one phase with duration_min=5, repeat=4 followed by one with duration_min=3, repeat=4)

## IMPORTANT: CALL final_answer IMMEDIATELY
Do not write long text introductions. You must formulate the weekly plan and call the `final_answer` tool with the structured plan.

Here is an example structure of the arguments for calling `final_answer`:
{{
  "coach_rationale": "Weekly periodisation rationale explaining the block structure...",
  "daily_workouts": [
    {{
      "day_of_week": 1,
      "name": "Tempo Endurance",
      "workout_type": "endurance",
      "sport": "cycling",
      "target_tss": 75,
      "rationale": "Controlled aerobic development.",
      "coach_notes": "Stay focused on cadence.",
      "phases": [
        {{"name": "Warmup", "duration_min": 15, "zone": "Z2", "target_power_pct": 65, "repeat": 1}},
        {{"name": "Tempo Block", "duration_min": 40, "zone": "Z3", "target_power_pct": 82, "repeat": 1}},
        {{"name": "Cooldown", "duration_min": 10, "zone": "Z1", "target_power_pct": 55, "repeat": 1}}
      ]
    }}
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
