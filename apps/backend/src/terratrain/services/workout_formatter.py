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

from terratrain.schemas.workout import WorkoutPhase, WorkoutPlan


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
        if phase.target_hr_zone is not None:
            return f"@{phase.target_hr_zone}bpm"
        zone_power_map = {
            "Z1": 50, "Z2": 65, "Z3": 82, "Z4": 94,
            "Z5": 108, "Z6": 130, "Z7": 155,
        }
        pct = zone_power_map.get(phase.zone.upper(), 65)
        return f"@{pct}%FTP"

    @staticmethod
    def _format_duration(minutes: float) -> str:
        total_sec = int(minutes * 60)
        if total_sec % 60 == 0:
            return f"{int(minutes)}min"
        return f"{total_sec}sec"

    @staticmethod
    def validate(plan: WorkoutPlan) -> list[str]:
        """Return a list of validation error strings (empty = valid)."""
        errors: list[str] = []
        total_min = sum(p.duration_min for p in plan.phases)
        if total_min < 10:
            errors.append(f"Total duration {total_min:.0f} min is less than 10 min")
        if total_min > 360:
            errors.append(f"Total duration {total_min:.0f} min exceeds 6 hours")
        if not plan.phases:
            errors.append("Workout has no phases")
        if plan.target_tss <= 0:
            errors.append("target_tss must be positive")
        return errors
