"""AI coaching agent — hand-written tool-use loop over Ollama.

Architecture:
  1. Assemble context: athlete profile + PMC load + route terrain + RAG
  2. Build system prompt
  3. Run agent loop (max N turns, Ollama tool-use API)
  4. Parse WorkoutPlan structured output
  5. Validate + format to Intervals.icu DSL
  6. Persist and optionally push
"""

from __future__ import annotations

import json
from collections.abc import AsyncGenerator
from datetime import date
from typing import Any

import httpx
import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from terratrain.config import get_settings
from terratrain.constants import Sport
from terratrain.db.models.athlete import Athlete
from terratrain.db.models.route import Route
from terratrain.db.models.workout import Workout
from terratrain.schemas.workout import StrengthExercise, WorkoutPhase, WorkoutPlan
from terratrain.services.rag_service import RagService
from terratrain.services.training_analytics import TrainingAnalytics
from terratrain.services.workout_formatter import WorkoutFormatter
from terratrain.services.workout_normalizer import normalize_workout_duration

logger = structlog.get_logger()


class OllamaError(Exception):
    """Raised when the Ollama chat backend is unreachable or misconfigured."""


# JSON schema for the final_answer tool — forces structured WorkoutPlan output.
# `phases` (endurance: cycling/running/swimming/cross_country_skiing) and
# `exercises` (weight_training) are mutually exclusive — neither is marked
# `required` here since which one applies depends on `sport`; the actual
# per-sport requirement is enforced by WorkoutFormatter.validate() in Python.
WORKOUT_PLAN_TOOL_SCHEMA = {
    "type": "object",
    "required": ["name", "workout_type", "sport", "target_tss", "rationale"],
    "properties": {
        "name": {"type": "string"},
        "workout_type": {"type": "string"},
        "sport": {"type": "string", "enum": [s.value for s in Sport]},
        "phases": {
            "type": "array",
            "description": "Endurance sports only (cycling/running/swimming/cross_country_skiing).",
            "items": {
                "type": "object",
                "required": ["name", "duration_min", "zone"],
                "properties": {
                    "name": {"type": "string"},
                    "duration_min": {"type": "number"},
                    "zone": {"type": "string"},
                    "target_power_pct": {"type": "number"},
                    "target_hr_zone": {"type": "string"},
                    "target_cadence_rpm": {
                        "type": "integer",
                        "description": "Cycling only — optional target cadence in rpm (e.g. 90, 95, 100).",
                    },
                    "description": {"type": "string"},
                    "repeat": {"type": "integer", "default": 1},
                },
            },
        },
        "exercises": {
            "type": "array",
            "description": "weight_training only.",
            "items": {
                "type": "object",
                "required": ["name", "sets", "reps"],
                "properties": {
                    "name": {"type": "string"},
                    "sets": {"type": "integer"},
                    "reps": {"type": "integer"},
                    "rpe": {"type": "number", "description": "1-10 scale, 10 = failure."},
                    "rest_seconds": {"type": "integer"},
                    "description": {"type": "string"},
                },
            },
        },
        "target_tss": {"type": "number"},
        "rationale": {"type": "string"},
        "coach_notes": {"type": "string", "default": ""},
    },
}

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "query_training_science",
            "description": "Search the training science knowledge base for relevant research.",
            "parameters": {
                "type": "object",
                "required": ["topic"],
                "properties": {"topic": {"type": "string"}},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "calculate_zones",
            "description": "Return cycling power zone boundaries as percentage of FTP.",
            "parameters": {
                "type": "object",
                "required": ["ftp"],
                "properties": {
                    "ftp": {"type": "integer"},
                    "model": {"type": "string", "default": "coggan_classic"},
                },
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
                "required": ["threshold_pace_s_per_m"],
                "properties": {"threshold_pace_s_per_m": {"type": "number"}},
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
                "required": ["css_pace_s_per_100m"],
                "properties": {"css_pace_s_per_100m": {"type": "number"}},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "calculate_hr_zones",
            "description": (
                "Return heart-rate zone boundaries relative to LTHR "
                "(used for cross_country_skiing, where power/pace aren't practical)."
            ),
            "parameters": {
                "type": "object",
                "required": ["lthr"],
                "properties": {"lthr": {"type": "integer"}},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "estimate_tss",
            "description": "Estimate Training Stress Score for a planned workout.",
            "parameters": {
                "type": "object",
                "required": ["duration_min", "intensity_factor"],
                "properties": {
                    "duration_min": {"type": "number"},
                    "intensity_factor": {"type": "number"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "final_answer",
            "description": "Submit the completed workout plan. Call this when ready.",
            "parameters": WORKOUT_PLAN_TOOL_SCHEMA,
        },
    },
]


class CoachingAgent:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._settings = get_settings()
        self._rag = RagService(session=session)

    async def generate(
        self,
        athlete: Athlete,
        route: Route | None,
        workout_type: str,
        sport: str | None = None,
        aggressiveness: int = 0,
        scheduled_date: date | None = None,
        notes: str | None = None,
        auto_push: bool = False,
        provider: str | None = None,
        press_lap: bool = False,
    ) -> AsyncGenerator[dict[str, Any], None]:
        yield {"event": "thinking", "data": "Gathering athlete context..."}

        llm_provider = provider or self._settings.resolved_llm_provider
        active_sport = sport or athlete.sport

        # Step 1: assemble context concurrently
        pmc = await self._get_pmc(athlete)
        rag_chunks = await self._rag.retrieve(f"{workout_type} training prescription", top_k=5)

        yield {"event": "thinking", "data": "Analyzing route terrain..."}

        context = self._build_context(
            athlete, pmc, route, rag_chunks, workout_type, notes, sport=active_sport, aggressiveness=aggressiveness
        )
        system_prompt = self._build_system_prompt(context)

        yield {"event": "thinking", "data": "Starting coaching agent loop..."}

        # Step 2: agent loop with validation-feedback retry
        messages: list[dict] = [{"role": "user", "content": system_prompt}]
        plan: WorkoutPlan | None = None
        validation_retries_left = 1
        max_turns = self._settings.ollama_max_agent_turns + 2  # headroom for retry

        for turn in range(max_turns):
            yield {"event": "thinking", "data": f"Agent turn {turn + 1}..."}

            try:
                response = await self._call_llm(messages, llm_provider)
            except OllamaError as exc:
                yield {"event": "error", "data": str(exc)}
                return

            assistant_msg = response.get("message", {})
            messages.append(assistant_msg)

            tool_calls = assistant_msg.get("tool_calls", [])
            if not tool_calls:
                yield {"event": "thinking", "data": assistant_msg.get("content", "")}
                continue

            plan_data: dict | None = None
            for tc in tool_calls:
                fn_name = tc.get("function", {}).get("name", "")
                fn_args = tc.get("function", {}).get("arguments", {})

                yield {"event": "tool_call", "data": f"{fn_name}({json.dumps(fn_args)[:120]})"}

                if fn_name == "final_answer":
                    plan_data = fn_args
                    break

                result = await self._execute_tool(fn_name, fn_args)
                yield {"event": "tool_result", "data": f"{fn_name} → {str(result)[:200]}"}

                tool_msg = {
                    "role": "tool",
                    "content": json.dumps(result),
                }
                if tc.get("id"):
                    tool_msg["tool_call_id"] = tc["id"]
                if fn_name:
                    tool_msg["name"] = fn_name
                messages.append(tool_msg)

            if plan_data is None:
                continue

            # Parse + validate the submitted plan
            try:
                plan_sport = plan_data.get("sport", active_sport)
                candidate = WorkoutPlan(
                    name=plan_data["name"],
                    workout_type=plan_data["workout_type"],
                    sport=plan_sport,
                    phases=[WorkoutPhase(**p) for p in plan_data.get("phases", [])],
                    exercises=[StrengthExercise(**e) for e in plan_data.get("exercises", [])],
                    target_tss=plan_data.get("target_tss", 0),
                    rationale=plan_data["rationale"],
                    coach_notes=plan_data.get("coach_notes", ""),
                )
                import re
                target_dur = 0.0
                if notes:
                    dur_match = re.search(r"(\d+)\s*(?:min|m|minute)", notes, re.IGNORECASE)
                    if dur_match:
                        target_dur = float(dur_match.group(1))
                # Duration normalization only makes sense for phase-based
                # (endurance) plans — weight_training has no `phases`.
                if target_dur > 0 and plan_sport != Sport.WEIGHT_TRAINING:
                    candidate = normalize_workout_duration(candidate, target_dur)
                validation_errors = WorkoutFormatter.validate(candidate)
            except Exception as exc:
                validation_errors = [f"Plan does not match the required schema: {exc}"]
                candidate = None  # type: ignore[assignment]

            if not validation_errors and candidate is not None:
                plan = candidate
                break

            if validation_retries_left > 0:
                validation_retries_left -= 1
                feedback = (
                    "Your workout plan was REJECTED by the validator. Problems:\n- "
                    + "\n- ".join(validation_errors)
                    + "\nFix these issues and call final_answer again with a corrected plan."
                )
                yield {
                    "event": "thinking",
                    "data": f"Plan rejected ({len(validation_errors)} issue(s)) — asking coach to revise...",
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
                continue

            yield {
                "event": "error",
                "data": "Validation failed after retry: " + "; ".join(validation_errors),
            }
            return

        if plan is None:
            yield {"event": "error", "data": "Agent did not produce a valid workout plan"}
            return

        structured_text = WorkoutFormatter.to_intervals_icu(plan, athlete=athlete)
        structured_text = WorkoutFormatter.apply_press_lap(structured_text, press_lap)
        yield {"event": "thinking", "data": "Saving workout..."}

        workout = await self._persist_workout(
            athlete=athlete,
            route=route,
            plan=plan,
            structured_text=structured_text,
            scheduled_date=scheduled_date,
            press_lap=press_lap,
        )

        if auto_push and athlete.intervals_api_key_encrypted:
            from terratrain.services.intervals_client import IntervalsClient

            client = IntervalsClient.from_athlete(athlete)
            intervals_id = await client.push_workout(workout)
            workout.intervals_workout_id = intervals_id
            workout.status = "pushed"
            await self._session.commit()
            yield {"event": "thinking", "data": "Workout pushed to Intervals.icu"}

        yield {
            "event": "workout_plan",
            "data": {
                "workout_id": str(workout.id),
                "name": plan.name,
                "structured_text": structured_text,
                "target_tss": plan.target_tss,
                "rationale": plan.rationale,
                "coach_notes": plan.coach_notes,
                "status": workout.status,
            },
        }

    async def _get_pmc(self, athlete: Athlete) -> dict:
        """Current training load — uses the shared fitness service, which
        falls back to Intervals.icu wellness for Strava-sourced athletes."""
        from terratrain.services.fitness_service import get_fitness

        fitness = await get_fitness(athlete, self._session, days=90)
        current = fitness["current"]
        weekly_tss = sum(p["tss"] for p in fitness["series"][-7:])
        return {
            "ctl": current["ctl"],
            "atl": current["atl"],
            "tsb": current["tsb"],
            "weekly_tss": round(weekly_tss, 1),
            "session_count": len([p for p in fitness["series"] if p["tss"] > 0]),
        }

    def _build_context(
        self,
        athlete: Athlete,
        pmc: dict,
        route: Route | None,
        rag_chunks: list[dict],
        workout_type: str,
        notes: str | None,
        sport: str | None = None,
        aggressiveness: int = 0,
    ) -> dict:
        context: dict = {
            "athlete": {
                "name": athlete.name,
                "sport": sport or athlete.sport,
                "ftp_watts": athlete.ftp_watts,
                "threshold_pace_s_per_m": athlete.threshold_pace_s_per_m,
                "css_pace_s_per_100m": athlete.css_pace_s_per_100m,
                "weight_kg": athlete.weight_kg,
                "lthr": athlete.lthr,
                "zones": athlete.training_zones,
            },
            "pmc": pmc,
            "workout_type": workout_type,
            "aggressiveness": aggressiveness,
            "notes": notes,
            "rag_context": [c["content"] for c in rag_chunks[:5]],
        }

        if route:
            context["route"] = {
                "name": route.name,
                "distance_km": round(route.distance_m / 1000, 1),
                "elevation_gain_m": round(route.elevation_gain_m, 0),
                "terrain_score": route.terrain_score,
                "climbs": route.climb_profile[:6],
            }

        return context

    # --- Sport-conditional prompt sections, shared with WeeklyCoachingAgent ---

    # Keyed by plain str (not the Sport enum members) so lookups against the
    # athlete's `sport: str` column/param type-check cleanly.
    _SPORT_COACH_LABELS = {
        Sport.CYCLING.value: "cycling",
        Sport.RUNNING.value: "running",
        Sport.SWIMMING.value: "swimming",
        Sport.CROSS_COUNTRY_SKIING.value: "cross-country skiing",
        Sport.WEIGHT_TRAINING.value: "strength training",
    }

    @staticmethod
    def _sport_label(sport: str) -> str:
        return CoachingAgent._SPORT_COACH_LABELS.get(sport, "endurance")

    @staticmethod
    def _athlete_profile_block(athlete: dict) -> str:
        """Athlete profile lines, showing only the threshold metric relevant
        to their sport (%FTP for cycling, pace for running, CSS for
        swimming, LTHR for skiing — weight_training has no continuous
        physiological threshold)."""
        sport = athlete["sport"]
        lines = [f"Name: {athlete['name']}", f"Sport: {sport}"]

        if sport == Sport.CYCLING:
            lines.append(f"FTP: {athlete['ftp_watts'] or 'unknown'} W")
        elif sport == Sport.RUNNING:
            tp = athlete.get("threshold_pace_s_per_m")
            pace = WorkoutFormatter._format_pace_per_km(tp) if tp else "unknown"
            lines.append(f"Threshold pace: {pace}")
        elif sport == Sport.SWIMMING:
            css = athlete.get("css_pace_s_per_100m")
            pace = WorkoutFormatter._format_pace_per_100m(css) if css else "unknown"
            lines.append(f"CSS (Critical Swim Speed): {pace}")
        elif sport == Sport.CROSS_COUNTRY_SKIING:
            lines.append(f"LTHR: {athlete['lthr'] or 'unknown'} bpm")

        lines.append(f"Weight: {athlete['weight_kg'] or 'unknown'} kg")
        return "\n".join(lines)

    @staticmethod
    def _sport_hard_rules_block(sport: str) -> str:
        if sport == Sport.CYCLING:
            return """- First phase = warmup: at most 75% FTP, at least 10 min
- Last phase = cooldown: at most 75% FTP
- REPEAT CALCULATION MATH: a set with `repeat: N` multiplies the total time! 3 repeats of 8 min work + 8 min recovery takes 3 * (8 + 8) = 48 minutes total!
- Intervals ABOVE 105% FTP: maximum 8 min each
- Threshold intervals (95-105% FTP): maximum 30 min each
- Total time at/above 95% FTP: maximum 60 min per session
- `target_power_pct` must be a NUMBER (e.g. 95), never a zone label
- `target_hr_zone` only as numeric bpm range like "130-145" — NEVER "Z2"
- For cycling phases, include appropriate target cadence in rpm via `target_cadence_rpm` (e.g. 90 rpm for endurance/warmup, 95-100 rpm for threshold/VO2max, 80-85 rpm for climbing/torque).
- Use `repeat` for interval sets
- `target_tss` must match the phases (validator recomputes it; ±30% tolerance)"""

        if sport in (Sport.RUNNING, Sport.SWIMMING, Sport.CROSS_COUNTRY_SKIING):
            return """- Use `phases` (this is a continuous-effort endurance sport) — do NOT use `exercises`.
- Set `zone` to Z1-Z5 to express intensity. Do NOT set `target_power_pct` — the \
app derives the athlete's actual pace/HR target from their own thresholds.
- First phase = warmup: zone Z1 or Z2, at least 10 min
- Last phase = cooldown: zone Z1
- REPEAT CALCULATION MATH: a set with `repeat: N` multiplies the total time! 3 repeats of 8 min work + 8 min recovery takes 3 * (8 + 8) = 48 minutes total!
- Zone Z5 (and above): maximum 8 min per interval
- Zone Z4 (threshold): maximum 30 min per interval
- Total time at/above zone Z4: maximum 60 min per session
- `target_tss` must match the phases (validator recomputes it; ±30% tolerance) \
— use it as your best estimate of relative training load"""

        # weight_training
        return """- Use `exercises` (NOT `phases`) — one entry per exercise with sets, reps, and RPE.
- Include 1-2 lighter warmup sets before working sets.
- `rpe` is 1-10 (Rate of Perceived Exertion, 10 = failure); typical working sets are RPE 6-8.
- `target_tss` is not meaningful for strength work — set it to 0.
- Do not populate `phases` for a weight_training workout."""

    @staticmethod
    def _sport_example_block(sport: str) -> str:
        if sport == Sport.WEIGHT_TRAINING:
            return """{
  "name": "Lower Body Strength",
  "workout_type": "strength",
  "sport": "weight_training",
  "target_tss": 0,
  "rationale": "Build posterior-chain strength to support endurance power output.",
  "coach_notes": "Focus on controlled eccentrics.",
  "exercises": [
    {"name": "Back Squat", "sets": 4, "reps": 8, "rpe": 7},
    {"name": "Romanian Deadlift", "sets": 3, "reps": 10, "rpe": 7, "rest_seconds": 90}
  ]
}"""
        return (
            """{
  "name": "Threshold Session",
  "workout_type": "threshold",
  "sport": \""""
            + sport
            + """",
  "target_tss": 60,
  "rationale": "Controlled aerobic development.",
  "coach_notes": "Stay relaxed and focused on form.",
  "phases": [
    {"name": "Warmup", "duration_min": 15, "zone": "Z2", "repeat": 1},
    {"name": "Threshold Block", "duration_min": 20, "zone": "Z4", "repeat": 1},
    {"name": "Cooldown", "duration_min": 10, "zone": "Z1", "repeat": 1}
  ]
}"""
        )

    def _build_system_prompt(self, ctx: dict) -> str:
        athlete = ctx["athlete"]
        sport = athlete["sport"]
        pmc = ctx["pmc"]
        rag = "\n---\n".join(ctx["rag_context"])

        aggressiveness = ctx.get("aggressiveness", 0)
        if aggressiveness > 0:
            agg_guide = f"HIGHER / AGGRESSIVE (+{aggressiveness}): Prescribe higher interval volume, longer work phases, and push target TSS towards upper limits (+15% to +30%)."
        elif aggressiveness < 0:
            agg_guide = f"LOWER / CONSERVATIVE ({aggressiveness}): Prescribe conservative interval volume, shorter work phases, and reduce target TSS (-15% to -30%) to prioritize freshness."
        else:
            agg_guide = "BALANCED / STANDARD (0): Standard baseline target load and interval prescription."

        prompt = f"""You are TerraTrain, an expert {self._sport_label(sport)} coach.

## Athlete Profile
{self._athlete_profile_block(athlete)}

## Current Training Load
CTL (fitness): {pmc["ctl"]}
ATL (fatigue): {pmc["atl"]}
TSB (form): {pmc["tsb"]} — {"fresh" if pmc["tsb"] > 5 else "fatigued" if pmc["tsb"] < -10 else "neutral"}
Weekly TSS: {pmc["weekly_tss"]}

## Requested Workout
Type: {ctx["workout_type"]}
Training Load Aggressiveness: {agg_guide}
Notes: {ctx.get("notes") or "none"}
"""

        if "route" in ctx:
            route = ctx["route"]
            prompt += f"""
## Route
Name: {route["name"]}
Distance: {route["distance_km"]} km
Elevation gain: {route["elevation_gain_m"]} m
Terrain score: {route["terrain_score"]} (0=flat, 1=very hilly)
"""
            if route["climbs"]:
                prompt += "Key climbs:\n"
                for c in route["climbs"]:
                    start_km = c.get("start_km", 0.0)
                    end_km = c.get("end_km", 0.0)
                    start_min = round(start_km * (60.0 / 23.0))
                    end_min = round(end_km * (60.0 / 23.0))
                    cat_str = f" ({c['category']})" if c.get("category") else ""
                    prompt += (
                        f"  - km {start_km}–{end_km} (ESTIMATED RIDE WINDOW: min {start_min} to min {end_min}), "
                        f"{c['avg_grade_pct']}% avg grade, {c['elevation_gain_m']} m gain{cat_str}\n"
                    )

        if rag:
            prompt += f"""
## Training Science Context
{rag}
"""

        prompt += f"""
## Instructions
Design a structured workout that:
1. Fits the athlete's current form (TSB) and training load
2. Places high-intensity intervals ON the climbs (between climb start_km and end_km) if a route is provided. Warmup/prep must end right when reaching the climb.
3. Follows evidence-based periodization from the training science context
4. Produces a realistic, safe training stress

## HARD RULES — plans violating these are rejected automatically
{self._sport_hard_rules_block(sport)}

## Example of a GOOD plan for this sport
{self._sport_example_block(sport)}

Use your tools to check zones, estimate TSS, or query more science.
When ready, call final_answer with the complete workout plan.
"""
        return prompt

    async def _execute_tool(self, name: str, args: dict) -> object:
        """Execute a tool call. Errors are returned as results (never raised)
        so a bad argument from the LLM cannot kill the SSE stream."""
        try:
            if name == "query_training_science":
                chunks = await self._rag.retrieve(args.get("topic", ""), top_k=3)
                return [c["content"] for c in chunks]

            if name == "calculate_zones":
                model = args.get("model") or "coggan_classic"
                if model not in ("coggan_classic",):
                    model = "coggan_classic"  # LLMs invent model names — normalize
                return TrainingAnalytics.calculate_zones(ftp=args["ftp"], model=model)

            if name == "calculate_running_pace_zones":
                return TrainingAnalytics.calculate_running_pace_zones(
                    threshold_pace_s_per_m=float(args["threshold_pace_s_per_m"])
                )

            if name == "calculate_swim_css_zones":
                return TrainingAnalytics.calculate_swim_css_zones(
                    css_pace_s_per_100m=float(args["css_pace_s_per_100m"])
                )

            if name == "calculate_hr_zones":
                return TrainingAnalytics.calculate_hr_zones(lthr=int(args["lthr"]))

            if name == "estimate_tss":
                return TrainingAnalytics.estimate_tss(
                    duration_min=float(args["duration_min"]),
                    intensity_factor=float(args["intensity_factor"]),
                )

            return {"error": f"Unknown tool: {name}"}
        except Exception as exc:
            logger.warning("coaching.tool_failed", tool=name, error=str(exc))
            return {"error": f"Tool {name} failed: {exc}"}

    async def _call_ollama(self, messages: list[dict]) -> dict:
        settings = self._settings
        try:
            async with httpx.AsyncClient(timeout=settings.ollama_request_timeout) as client:
                resp = await client.post(
                    f"{settings.ollama_base_url}/api/chat",
                    json={
                        "model": settings.ollama_chat_model,
                        "messages": messages,
                        "tools": TOOLS,
                        "stream": False,
                        "options": {"temperature": 0.3},
                    },
                )
        except httpx.HTTPError as exc:
            raise OllamaError(
                f"Could not reach the AI service at {settings.ollama_base_url}. "
                f"Is Ollama running? ({exc})"
            ) from exc

        if resp.status_code == 404:
            raise OllamaError(
                f"The AI model '{settings.ollama_chat_model}' is not installed. "
                f"Run 'make pull-models-gpu' to download it, then try again."
            )
        if resp.status_code >= 400:
            raise OllamaError(
                f"The AI model returned an error (HTTP {resp.status_code}): {resp.text[:200]}"
            )
        return resp.json()

    async def _call_llm(self, messages: list[dict], provider: str) -> dict:
        if provider == "gemini":
            return await self._call_gemini(messages)
        return await self._call_ollama(messages)

    async def _call_gemini(self, messages: list[dict]) -> dict:
        settings = self._settings
        if not settings.gemini_api_key:
            raise OllamaError("GEMINI_API_KEY is not set. Please set it in your .env file.")

        headers = {
            "Authorization": f"Bearer {settings.gemini_api_key}",
            "Content-Type": "application/json",
        }

        import json
        formatted_messages = []
        for msg in messages:
            msg_copy = dict(msg)
            if "tool_calls" in msg_copy:
                tool_calls_copy = []
                for tc in msg_copy["tool_calls"]:
                    tc_copy = dict(tc)
                    fn_copy = dict(tc_copy.get("function", {}))
                    args = fn_copy.get("arguments")
                    if isinstance(args, dict):
                        fn_copy["arguments"] = json.dumps(args)
                    tc_copy["function"] = fn_copy
                    tool_calls_copy.append(tc_copy)
                msg_copy["tool_calls"] = tool_calls_copy
            formatted_messages.append(msg_copy)

        gemini_tools = [t for t in TOOLS if t["function"]["name"] == "final_answer"]

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

    async def _persist_workout(
        self,
        athlete: Athlete,
        route: Route | None,
        plan: WorkoutPlan,
        structured_text: str,
        scheduled_date: date | None,
        press_lap: bool = False,
    ) -> Workout:
        # weight_training plans have no `phases` (they use `exercises` instead,
        # which carry no per-set duration estimate) — duration is unknown.
        duration_seconds = None
        if plan.sport != Sport.WEIGHT_TRAINING:
            total_min = sum(p.duration_min * max(1, p.repeat) for p in plan.phases)
            duration_seconds = int(total_min * 60)

        workout = Workout(
            athlete_id=athlete.id,
            route_id=route.id if route else None,
            name=plan.name,
            sport=plan.sport,
            workout_type=plan.workout_type,
            scheduled_date=scheduled_date,
            duration_seconds=duration_seconds,
            target_tss=plan.target_tss,
            structured_text=structured_text,
            press_lap=press_lap,
            llm_plan=plan.model_dump(),
            llm_reasoning=plan.rationale,
            coach_notes=plan.coach_notes,
            status="draft",
        )
        self._session.add(workout)
        await self._session.commit()
        await self._session.refresh(workout)
        return workout
