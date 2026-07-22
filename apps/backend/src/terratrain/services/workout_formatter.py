"""Deterministic formatter: WorkoutPlan → Intervals.icu structured text DSL.

The LLM produces a WorkoutPlan (structured Pydantic model).
This module converts it to the Intervals.icu workout text format.

Format reference (cycling, %FTP):
  Warmup(15min @65%FTP)
  3x(8min @95%FTP, 2min @55%FTP)
  Cooldown(10min @60%FTP)

For running/swimming/cross_country_skiing, the same phase structure is used
but each phase's `zone` (Z1-Z5) is resolved against the athlete's own
threshold-relative zone table (pace, CSS pace, or HR — see
services/training_analytics.py) instead of %FTP. weight_training uses an
entirely different plan shape (`exercises`, not `phases`) since sets/reps/RPE
don't fit a duration+intensity-target model at all.

The LLM never writes raw DSL — it writes intent (zone, power%, duration, or
exercise/sets/reps/RPE), this module translates deterministically.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from terratrain.constants import Sport
from terratrain.schemas.workout import WorkoutPhase, WorkoutPlan
from terratrain.services.training_analytics import TrainingAnalytics

if TYPE_CHECKING:
    from terratrain.db.models.athlete import Athlete

# Valid HR targets: "140" or "130-145" (2-3 digit bpm values)
_HR_PATTERN = re.compile(r"^\d{2,3}(-\d{2,3})?$")

# Fallback power % when only a zone label is given (cycling)
_ZONE_POWER_MAP = {
    "Z1": 50,
    "Z2": 65,
    "Z3": 82,
    "Z4": 94,
    "Z5": 108,
    "Z6": 130,
    "Z7": 155,
}

# Prepended as the very first line when Workout.press_lap is enabled, so the
# athlete's device prompts a manual lap press before the workout starts.
PRESS_LAP_LINE = "- Press lap"


class WorkoutFormatter:
    @staticmethod
    def to_intervals_icu(plan: WorkoutPlan, athlete: Athlete | None = None) -> str:
        """Convert a WorkoutPlan to Intervals.icu workout text."""
        if plan.sport == Sport.WEIGHT_TRAINING:
            return WorkoutFormatter._format_strength_plan(plan)

        lines: list[str] = []

        i = 0
        phases = plan.phases

        while i < len(phases):
            phase = phases[i]

            # Look-ahead: check for repeat groups
            if phase.repeat > 1 and i + 1 < len(phases):
                group_phases = WorkoutFormatter._collect_group(phases, i)

                # Add empty line before repeat block if needed
                if lines and lines[-1] != "":
                    lines.append("")

                block = WorkoutFormatter._format_repeat_block(
                    group_phases, phase.repeat, plan.sport, athlete
                )
                lines.append(block)

                # Add empty line after repeat block
                lines.append("")
                i += len(group_phases)
            else:
                lines.append(WorkoutFormatter._format_phase(phase, plan.sport, athlete))
                i += 1

        # Clean up consecutive empty lines and trailing empty lines
        final_lines: list[str] = []
        for item in lines:
            sublines = item.split("\n")
            for line in sublines:
                if line == "":
                    if final_lines and final_lines[-1] != "":
                        final_lines.append("")
                else:
                    final_lines.append(line)

        if final_lines and final_lines[-1] == "":
            final_lines.pop()

        return "\n".join(final_lines)

    @staticmethod
    def apply_press_lap(structured_text: str, enabled: bool) -> str:
        """Add or remove the leading "- Press lap" line to match `enabled`.

        Idempotent either way: calling with the same `enabled` value twice
        leaves the text unchanged, so this is safe to call both at workout
        generation time and whenever the Workout.press_lap flag is toggled
        later via an update.
        """
        lines = structured_text.split("\n") if structured_text else []
        has_marker = bool(lines) and lines[0].strip() == PRESS_LAP_LINE

        if enabled and not has_marker:
            lines.insert(0, PRESS_LAP_LINE)
        elif not enabled and has_marker:
            lines.pop(0)
            while lines and lines[0] == "":
                lines.pop(0)

        return "\n".join(lines)

    @staticmethod
    def _collect_group(phases: list[WorkoutPhase], start: int) -> list[WorkoutPhase]:
        """Collect consecutive phases that are part of the same repeat block."""
        repeat = phases[start].repeat
        group = []
        for p in phases[start:]:
            if p.repeat == repeat:
                group.append(p)
            else:
                break
        return group

    @staticmethod
    def _format_phase(phase: WorkoutPhase, sport: str, athlete: Athlete | None) -> str:
        target = WorkoutFormatter._format_target(phase, sport, athlete)
        duration_str = WorkoutFormatter._format_duration(phase.duration_min)
        name = phase.name.strip()
        if name:
            return f"- {name} {duration_str} {target}"
        return f"- {duration_str} {target}"

    @staticmethod
    def _format_repeat_block(
        phases: list[WorkoutPhase], repeat: int, sport: str, athlete: Athlete | None
    ) -> str:
        lines = [f"{repeat}x"]
        for p in phases:
            target = WorkoutFormatter._format_target(p, sport, athlete)
            duration_str = WorkoutFormatter._format_duration(p.duration_min)
            name = p.name.strip()
            if name:
                lines.append(f"- {name} {duration_str} {target}")
            else:
                lines.append(f"- {duration_str} {target}")
        return "\n".join(lines)

    @staticmethod
    def _format_target(phase: WorkoutPhase, sport: str, athlete: Athlete | None) -> str:
        if sport == Sport.CYCLING:
            return WorkoutFormatter._format_cycling_target(phase)
        if sport == Sport.RUNNING and athlete is not None and athlete.threshold_pace_s_per_m:
            zones = TrainingAnalytics.calculate_running_pace_zones(athlete.threshold_pace_s_per_m)
            z = zones.get(phase.zone.lower())
            if z:
                return WorkoutFormatter._format_pace_range(
                    z["min_pace_s_per_m"], z["max_pace_s_per_m"], per_100m=False
                )
        if sport == Sport.SWIMMING and athlete is not None and athlete.css_pace_s_per_100m:
            zones = TrainingAnalytics.calculate_swim_css_zones(athlete.css_pace_s_per_100m)
            z = zones.get(phase.zone.lower())
            if z:
                return WorkoutFormatter._format_pace_range(
                    z["min_pace_s_per_100m"], z["max_pace_s_per_100m"], per_100m=True
                )
        if sport == Sport.CROSS_COUNTRY_SKIING and athlete is not None and athlete.lthr:
            zones = TrainingAnalytics.calculate_hr_zones(athlete.lthr)
            z = zones.get(phase.zone.lower())
            if z:
                return f"{z['min_bpm']}-{z['max_bpm']}bpm"

        # No athlete threshold data available (or an unrecognized zone label) —
        # degrade gracefully to the plain zone name rather than fabricating a
        # target, matching this codebase's convention elsewhere (e.g. rag_service).
        return phase.zone.upper()

    @staticmethod
    def _format_cycling_target(phase: WorkoutPhase) -> str:
        if phase.target_power_pct is not None:
            return f"{int(phase.target_power_pct)}%"
        # HR target only if it's a real bpm value/range ("140" / "130-145").
        # LLMs sometimes put a zone label ("Z2") here — that would render as
        # invalid "@Z2bpm", so fall through to the zone power map instead.
        if phase.target_hr_zone is not None and _HR_PATTERN.match(phase.target_hr_zone.strip()):
            return f"{phase.target_hr_zone.strip()}bpm"
        pct = _ZONE_POWER_MAP.get(phase.zone.upper(), 65)
        return f"{pct}%"

    @staticmethod
    def _format_pace_per_km(s_per_m: float) -> str:
        total_sec = round(s_per_m * 1000)
        minutes, seconds = divmod(total_sec, 60)
        return f"{minutes}:{seconds:02d}/km"

    @staticmethod
    def _format_pace_per_100m(s_per_100m: float) -> str:
        total_sec = round(s_per_100m)
        minutes, seconds = divmod(total_sec, 60)
        return f"{minutes}:{seconds:02d}/100m"

    @staticmethod
    def _format_pace_range(min_pace: float, max_pace: float | None, *, per_100m: bool) -> str:
        fmt = (
            WorkoutFormatter._format_pace_per_100m
            if per_100m
            else WorkoutFormatter._format_pace_per_km
        )
        if max_pace is None:
            return f"slower than {fmt(min_pace)}"
        return f"{fmt(min_pace)}-{fmt(max_pace)}"

    @staticmethod
    def _format_duration(minutes: float) -> str:
        total_sec = int(minutes * 60)
        if total_sec % 60 == 0:
            return f"{int(minutes)}m"
        return f"{total_sec}s"

    @staticmethod
    def _phase_intensity_pct(phase: WorkoutPhase) -> float:
        """Effective relative intensity % of a phase (explicit %FTP or zone fallback).

        Used only for the sport-agnostic physiological plausibility checks in
        `validate()` — a proxy scale, not the rendered target (see
        `_format_target` for the sport-correct pace/HR/%FTP target text).
        """
        if phase.target_power_pct is not None:
            return phase.target_power_pct
        return float(_ZONE_POWER_MAP.get(phase.zone.upper(), 65))

    @staticmethod
    def _format_strength_plan(plan: WorkoutPlan) -> str:
        """Render a weight-training plan as exercise/sets/reps/RPE lines.

        Unlike endurance sports, strength work has no continuous duration or
        power/pace/HR target — each line is one exercise prescription.
        """
        lines: list[str] = []
        for ex in plan.exercises:
            detail = f"{ex.sets}x{ex.reps}"
            if ex.rpe is not None:
                detail += f" RPE {ex.rpe:g}"
            if ex.rest_seconds:
                detail += f", rest {ex.rest_seconds}s"
            name = ex.name.strip()
            line = f"- {name} {detail}" if name else f"- {detail}"
            if ex.description.strip():
                line += f" — {ex.description.strip()}"
            lines.append(line)
        return "\n".join(lines)

    @staticmethod
    def validate(plan: WorkoutPlan) -> list[str]:
        """Return a list of validation error strings (empty = valid)."""
        if plan.sport == Sport.WEIGHT_TRAINING:
            return WorkoutFormatter._validate_strength(plan)
        return WorkoutFormatter._validate_endurance(plan)

    @staticmethod
    def _validate_strength(plan: WorkoutPlan) -> list[str]:
        errors: list[str] = []
        if not plan.exercises:
            errors.append("Strength workout has no exercises")
            return errors

        for ex in plan.exercises:
            if ex.sets <= 0 or ex.reps <= 0:
                errors.append(f"Exercise '{ex.name}': sets and reps must both be positive")
            if ex.rpe is not None and not (1 <= ex.rpe <= 10):
                errors.append(f"Exercise '{ex.name}': RPE {ex.rpe:g} must be between 1 and 10")
            if ex.rest_seconds is not None and ex.rest_seconds < 0:
                errors.append(f"Exercise '{ex.name}': rest_seconds cannot be negative")
        return errors

    @staticmethod
    def _validate_endurance(plan: WorkoutPlan) -> list[str]:
        """Physiological plausibility rules so the LLM cannot prescribe
        impossible endurance sessions (e.g. 4x45min at max effort).

        The relative-intensity scale (`_phase_intensity_pct` / `_ZONE_POWER_MAP`)
        is reused across all endurance sports as a proxy for "how hard", so
        error wording says "relative intensity" outside cycling rather than
        the sport-inappropriate "% FTP".
        """
        errors: list[str] = []
        if not plan.phases:
            errors.append("Workout has no phases")
            return errors

        unit = "% FTP" if plan.sport == Sport.CYCLING else "% relative intensity"

        total_min = sum(p.duration_min * max(1, p.repeat) for p in plan.phases)
        if total_min < 10:
            errors.append(f"Total duration {total_min:.0f} min is less than 10 min")
        if total_min > 360:
            errors.append(f"Total duration {total_min:.0f} min exceeds 6 hours")
        if plan.target_tss <= 0:
            errors.append("target_tss must be positive")

        # Physiological interval caps
        time_at_or_above_95 = 0.0
        for p in plan.phases:
            pct = WorkoutFormatter._phase_intensity_pct(p)
            reps = max(1, p.repeat)
            if pct > 105 and p.duration_min > 8:
                errors.append(
                    f"Phase '{p.name}': {p.duration_min:.0f} min at {pct:.0f}{unit} — "
                    f"intervals above 105{unit} must be 8 min or shorter"
                )
            elif 95 <= pct <= 105 and p.duration_min > 30:
                errors.append(
                    f"Phase '{p.name}': {p.duration_min:.0f} min at {pct:.0f}{unit} — "
                    f"threshold intervals (95-105{unit}) must be 30 min or shorter"
                )
            if pct >= 95:
                time_at_or_above_95 += p.duration_min * reps

        if time_at_or_above_95 > 60:
            errors.append(
                f"Total time at/above 95{unit} is {time_at_or_above_95:.0f} min — "
                f"maximum is 60 min per session"
            )

        # Warmup / cooldown presence
        first, last = plan.phases[0], plan.phases[-1]
        first_pct = WorkoutFormatter._phase_intensity_pct(first)
        last_pct = WorkoutFormatter._phase_intensity_pct(last)
        if first_pct > 75 or first.duration_min < 5:
            errors.append(f"First phase must be a warmup: at most 75{unit} and at least 5 min")
        if last_pct > 75:
            errors.append(f"Last phase must be a cooldown at 75{unit} or below")

        # TSS consistency: recompute from phases, allow ±30% deviation
        est_tss = 0.0
        for p in plan.phases:
            intensity = WorkoutFormatter._phase_intensity_pct(p) / 100.0
            est_tss += (p.duration_min * max(1, p.repeat) / 60.0) * (intensity**2) * 100
        if plan.target_tss > 0 and est_tss > 0:
            deviation = abs(est_tss - plan.target_tss) / est_tss
            if deviation > 0.30:
                errors.append(
                    f"target_tss {plan.target_tss:.0f} deviates {deviation * 100:.0f}% "
                    f"from the TSS implied by the phases (~{est_tss:.0f}) — "
                    f"set target_tss to approximately {est_tss:.0f}"
                )

        return errors
