"""Deterministic formatter: WorkoutPlan → Intervals.icu structured text DSL.

The LLM produces a WorkoutPlan (structured Pydantic model).
This module converts it to the Intervals.icu workout text format.

Format reference:
  Warmup(15min @65%FTP)
  3x(8min @95%FTP, 2min @55%FTP)
  Cooldown(10min @60%FTP)

The LLM never writes raw DSL — it writes intent (zone, power%, duration),
this module translates deterministically.
"""

from __future__ import annotations

import re

from terratrain.schemas.workout import WorkoutPhase, WorkoutPlan

# Valid HR targets: "140" or "130-145" (2-3 digit bpm values)
_HR_PATTERN = re.compile(r"^\d{2,3}(-\d{2,3})?$")

# Fallback power % when only a zone label is given
_ZONE_POWER_MAP = {
    "Z1": 50,
    "Z2": 65,
    "Z3": 82,
    "Z4": 94,
    "Z5": 108,
    "Z6": 130,
    "Z7": 155,
}


class WorkoutFormatter:
    @staticmethod
    def to_intervals_icu(plan: WorkoutPlan) -> str:
        """Convert a WorkoutPlan to Intervals.icu workout text."""
        parts: list[str] = []

        i = 0
        phases = plan.phases

        while i < len(phases):
            phase = phases[i]

            # Look-ahead: check for repeat groups
            if phase.repeat > 1 and i + 1 < len(phases):
                group_phases = WorkoutFormatter._collect_group(phases, i)
                block = WorkoutFormatter._format_repeat_block(group_phases, phase.repeat)
                parts.append(block)
                i += len(group_phases)
            else:
                parts.append(WorkoutFormatter._format_phase(phase))
                i += 1

        return "\n".join(parts)

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
    def _format_phase(phase: WorkoutPhase) -> str:
        target = WorkoutFormatter._format_target(phase)
        duration_str = WorkoutFormatter._format_duration(phase.duration_min)
        name = phase.name
        return f"{name}({duration_str} {target})"

    @staticmethod
    def _format_repeat_block(phases: list[WorkoutPhase], repeat: int) -> str:
        inner_parts = []
        for p in phases:
            target = WorkoutFormatter._format_target(p)
            duration_str = WorkoutFormatter._format_duration(p.duration_min)
            inner_parts.append(f"{duration_str} {target}")
        inner = ", ".join(inner_parts)
        return f"{repeat}x({inner})"

    @staticmethod
    def _format_target(phase: WorkoutPhase) -> str:
        if phase.target_power_pct is not None:
            return f"@{int(phase.target_power_pct)}%FTP"
        # HR target only if it's a real bpm value/range ("140" / "130-145").
        # LLMs sometimes put a zone label ("Z2") here — that would render as
        # invalid "@Z2bpm", so fall through to the zone power map instead.
        if phase.target_hr_zone is not None and _HR_PATTERN.match(phase.target_hr_zone.strip()):
            return f"@{phase.target_hr_zone.strip()}bpm"
        pct = _ZONE_POWER_MAP.get(phase.zone.upper(), 65)
        return f"@{pct}%FTP"

    @staticmethod
    def _format_duration(minutes: float) -> str:
        total_sec = int(minutes * 60)
        if total_sec % 60 == 0:
            return f"{int(minutes)}min"
        return f"{total_sec}sec"

    @staticmethod
    def _phase_power_pct(phase: WorkoutPhase) -> float:
        """Effective power %FTP of a phase (explicit value or zone fallback)."""
        if phase.target_power_pct is not None:
            return phase.target_power_pct
        return float(_ZONE_POWER_MAP.get(phase.zone.upper(), 65))

    @staticmethod
    def validate(plan: WorkoutPlan) -> list[str]:
        """Return a list of validation error strings (empty = valid).

        Includes physiological plausibility rules so the LLM cannot
        prescribe impossible sessions (e.g. 4x45min @100% FTP).
        """
        errors: list[str] = []
        if not plan.phases:
            errors.append("Workout has no phases")
            return errors

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
            pct = WorkoutFormatter._phase_power_pct(p)
            reps = max(1, p.repeat)
            if pct > 105 and p.duration_min > 8:
                errors.append(
                    f"Phase '{p.name}': {p.duration_min:.0f} min at {pct:.0f}% FTP — "
                    f"intervals above 105% FTP must be 8 min or shorter"
                )
            elif 95 <= pct <= 105 and p.duration_min > 30:
                errors.append(
                    f"Phase '{p.name}': {p.duration_min:.0f} min at {pct:.0f}% FTP — "
                    f"threshold intervals (95-105% FTP) must be 30 min or shorter"
                )
            if pct >= 95:
                time_at_or_above_95 += p.duration_min * reps

        if time_at_or_above_95 > 60:
            errors.append(
                f"Total time at/above 95% FTP is {time_at_or_above_95:.0f} min — "
                f"maximum is 60 min per session"
            )

        # Warmup / cooldown presence
        first, last = plan.phases[0], plan.phases[-1]
        first_pct = WorkoutFormatter._phase_power_pct(first)
        last_pct = WorkoutFormatter._phase_power_pct(last)
        if first_pct > 75 or first.duration_min < 5:
            errors.append("First phase must be a warmup: at most 75% FTP and at least 5 min")
        if last_pct > 75:
            errors.append("Last phase must be a cooldown at 75% FTP or below")

        # TSS consistency: recompute from phases, allow ±30% deviation
        est_tss = 0.0
        for p in plan.phases:
            intensity = WorkoutFormatter._phase_power_pct(p) / 100.0
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
