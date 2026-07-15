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
from datetime import date, timezone
from typing import Any

import httpx
import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from terratrain.config import get_settings
from terratrain.db.models.athlete import Athlete
from terratrain.db.models.route import Route
from terratrain.db.models.session import TrainingSession
from terratrain.db.models.workout import Workout
from terratrain.schemas.workout import WorkoutPhase, WorkoutPlan
from terratrain.services.rag_service import RagService
from terratrain.services.training_analytics import TrainingAnalytics
from terratrain.services.workout_formatter import WorkoutFormatter

logger = structlog.get_logger()


class OllamaError(Exception):
    """Raised when the Ollama chat backend is unreachable or misconfigured."""

# JSON schema for the final_answer tool — forces structured WorkoutPlan output
WORKOUT_PLAN_TOOL_SCHEMA = {
    "type": "object",
    "required": ["name", "workout_type", "sport", "phases", "target_tss", "rationale"],
    "properties": {
        "name": {"type": "string"},
        "workout_type": {"type": "string"},
        "sport": {"type": "string"},
        "phases": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["name", "duration_min", "zone"],
                "properties": {
                    "name": {"type": "string"},
                    "duration_min": {"type": "number"},
                    "zone": {"type": "string"},
                    "target_power_pct": {"type": "number"},
                    "target_hr_zone": {"type": "string"},
                    "description": {"type": "string"},
                    "repeat": {"type": "integer", "default": 1},
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
            "description": "Return power zone boundaries as percentage of FTP.",
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
        scheduled_date: date | None,
        notes: str | None,
        auto_push: bool,
    ) -> AsyncGenerator[dict[str, Any], None]:
        yield {"event": "thinking", "data": "Gathering athlete context..."}

        # Step 1: assemble context concurrently
        pmc = await self._get_pmc(athlete)
        rag_chunks = await self._rag.retrieve(f"{workout_type} training prescription", top_k=5)

        yield {"event": "thinking", "data": "Analyzing route terrain..."}

        context = self._build_context(athlete, pmc, route, rag_chunks, workout_type, notes)
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
                response = await self._call_ollama(messages)
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

                messages.append({
                    "role": "tool",
                    "content": json.dumps(result),
                })

            if plan_data is None:
                continue

            # Parse + validate the submitted plan
            try:
                candidate = WorkoutPlan(
                    name=plan_data["name"],
                    workout_type=plan_data["workout_type"],
                    sport=plan_data.get("sport", athlete.sport),
                    phases=[WorkoutPhase(**p) for p in plan_data["phases"]],
                    target_tss=plan_data["target_tss"],
                    rationale=plan_data["rationale"],
                    coach_notes=plan_data.get("coach_notes", ""),
                )
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
                messages.append({"role": "tool", "content": feedback})
                continue

            yield {
                "event": "error",
                "data": "Validation failed after retry: " + "; ".join(validation_errors),
            }
            return

        if plan is None:
            yield {"event": "error", "data": "Agent did not produce a valid workout plan"}
            return

        structured_text = WorkoutFormatter.to_intervals_icu(plan)
        yield {"event": "thinking", "data": "Saving workout..."}

        workout = await self._persist_workout(
            athlete=athlete,
            route=route,
            plan=plan,
            structured_text=structured_text,
            scheduled_date=scheduled_date,
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
    ) -> dict:
        context: dict = {
            "athlete": {
                "name": athlete.name,
                "sport": athlete.sport,
                "ftp_watts": athlete.ftp_watts,
                "weight_kg": athlete.weight_kg,
                "lthr": athlete.lthr,
                "zones": athlete.training_zones,
            },
            "pmc": pmc,
            "workout_type": workout_type,
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

    def _build_system_prompt(self, ctx: dict) -> str:
        athlete = ctx["athlete"]
        pmc = ctx["pmc"]
        rag = "\n---\n".join(ctx["rag_context"])

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
TSB (form): {pmc["tsb"]} — {"fresh" if pmc["tsb"] > 5 else "fatigued" if pmc["tsb"] < -10 else "neutral"}
Weekly TSS: {pmc["weekly_tss"]}

## Requested Workout
Type: {ctx["workout_type"]}
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
                    prompt += (
                        f"  - {c['start_km']}–{c['end_km']} km, "
                        f"{c['avg_grade_pct']}% avg grade, "
                        f"{c['elevation_gain_m']} m gain"
                        f"{' (' + c['category'] + ')' if c.get('category') else ''}\n"
                    )

        if rag:
            prompt += f"""
## Training Science Context
{rag}
"""

        prompt += """
## Instructions
Design a structured workout that:
1. Fits the athlete's current form (TSB) and training load
2. Places intervals on climbs if a route is provided
3. Follows evidence-based periodization from the training science context
4. Produces a realistic, safe training stress (TSS)

## HARD RULES — plans violating these are rejected automatically
- First phase = warmup: at most 75% FTP, at least 10 min
- Last phase = cooldown: at most 75% FTP
- Intervals ABOVE 105% FTP: maximum 8 min each
- Threshold intervals (95-105% FTP): maximum 30 min each
- Total time at/above 95% FTP: maximum 60 min per session
- `target_power_pct` must be a NUMBER (e.g. 95), never a zone label
- `target_hr_zone` only as numeric bpm range like "130-145" — NEVER "Z2"
- Use `repeat` for interval sets (e.g. 4 reps of 5min on / 3min off:
  one phase with duration_min=5, repeat=4 followed by one with duration_min=3, repeat=4)
- `target_tss` must match the phases (validator recomputes it; ±30% tolerance)

## Example of a GOOD threshold plan (phases only)
[
  {"name": "Warmup", "duration_min": 15, "zone": "Z2", "target_power_pct": 65, "repeat": 1},
  {"name": "Threshold On", "duration_min": 12, "zone": "Z4", "target_power_pct": 96, "repeat": 3},
  {"name": "Recovery", "duration_min": 5, "zone": "Z1", "target_power_pct": 50, "repeat": 3},
  {"name": "Cooldown", "duration_min": 10, "zone": "Z1", "target_power_pct": 55, "repeat": 1}
]

Use your tools to check zones, estimate TSS, or query more science.
When ready, call final_answer with the complete workout plan.
"""
        return prompt

    async def _execute_tool(self, name: str, args: dict) -> object:
        if name == "query_training_science":
            chunks = await self._rag.retrieve(args.get("topic", ""), top_k=3)
            return [c["content"] for c in chunks]

        if name == "calculate_zones":
            return TrainingAnalytics.calculate_zones(
                ftp=args["ftp"],
                model=args.get("model", "coggan_classic"),
            )

        if name == "estimate_tss":
            return TrainingAnalytics.estimate_tss(
                duration_min=args["duration_min"],
                intensity_factor=args["intensity_factor"],
            )

        return {"error": f"Unknown tool: {name}"}

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
                f"The AI model returned an error (HTTP {resp.status_code}): "
                f"{resp.text[:200]}"
            )
        return resp.json()

    async def _persist_workout(
        self,
        athlete: Athlete,
        route: Route | None,
        plan: WorkoutPlan,
        structured_text: str,
        scheduled_date: date | None,
    ) -> Workout:
        from datetime import datetime

        total_min = sum(p.duration_min for p in plan.phases)
        workout = Workout(
            athlete_id=athlete.id,
            route_id=route.id if route else None,
            name=plan.name,
            sport=plan.sport,
            workout_type=plan.workout_type,
            scheduled_date=scheduled_date,
            duration_seconds=int(total_min * 60),
            target_tss=plan.target_tss,
            structured_text=structured_text,
            llm_plan=plan.model_dump(),
            llm_reasoning=plan.rationale,
            coach_notes=plan.coach_notes,
            status="draft",
        )
        self._session.add(workout)
        await self._session.commit()
        await self._session.refresh(workout)
        return workout
