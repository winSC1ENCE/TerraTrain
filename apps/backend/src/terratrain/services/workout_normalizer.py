import math
from terratrain.schemas.workout import WorkoutPhase, WorkoutPlan


def normalize_workout_duration(candidate: WorkoutPlan, target_duration_min: float) -> WorkoutPlan:
    """Ensure the sum of phase durations (accounting for repeat counts) strictly matches target_duration_min."""
    if not candidate.phases or target_duration_min <= 0:
        return candidate

    actual_min = sum(p.duration_min * max(1, p.repeat) for p in candidate.phases)
    diff = actual_min - target_duration_min

    # If already within 1 minute of target, keep as is
    if abs(diff) <= 1.0:
        return candidate

    phases = list(candidate.phases)

    if diff > 0:
        # Workout is TOO LONG. Reduce duration by `diff` minutes.
        # 1. Flexible non-high-intensity phases (target_power_pct <= 78 or zone Z1/Z2 or name keywords)
        flexible_indices = [
            i for i, p in enumerate(phases)
            if p.repeat <= 1 and p.duration_min > 3 and (
                (p.target_power_pct and p.target_power_pct <= 78) or
                any(kw in p.name.lower() or kw in (p.zone or "").lower() for kw in ["cooldown", "warmup", "prep", "endurance", "z1", "z2", "recovery", "spin", "steady", "commute", "easy"])
            )
        ]
        
        remaining_to_reduce = diff
        for idx in reversed(flexible_indices):
            p = phases[idx]
            min_allowed = 3.0 if any(kw in p.name.lower() for kw in ["cooldown", "warmup"]) else 5.0
            can_reduce = max(0.0, p.duration_min - min_allowed)
            reduction = min(remaining_to_reduce, can_reduce)
            if reduction > 0:
                phases[idx] = WorkoutPhase(
                    name=p.name,
                    duration_min=round(p.duration_min - reduction, 1),
                    zone=p.zone,
                    target_power_pct=p.target_power_pct,
                    target_hr_zone=p.target_hr_zone,
                    target_cadence_rpm=p.target_cadence_rpm,
                    description=p.description,
                    repeat=p.repeat,
                )
                remaining_to_reduce -= reduction
                if remaining_to_reduce <= 0.5:
                    break

        # 2. If still too long (because interval repeats were oversized), adjust repeat counts
        if remaining_to_reduce > 0.5:
            for idx, p in enumerate(phases):
                if p.repeat > 1:
                    single_cycle_min = p.duration_min
                    if idx + 1 < len(phases) and phases[idx + 1].repeat == p.repeat:
                        single_cycle_min += phases[idx + 1].duration_min
                    
                    if single_cycle_min > 0:
                        repeats_to_cut = math.ceil(remaining_to_reduce / single_cycle_min)
                        new_repeat = max(1, p.repeat - repeats_to_cut)
                        saved_min = (p.repeat - new_repeat) * single_cycle_min
                        
                        phases[idx] = WorkoutPhase(
                            name=p.name,
                            duration_min=p.duration_min,
                            zone=p.zone,
                            target_power_pct=p.target_power_pct,
                            target_hr_zone=p.target_hr_zone,
                            target_cadence_rpm=p.target_cadence_rpm,
                            description=p.description,
                            repeat=new_repeat,
                        )
                        if idx + 1 < len(phases) and phases[idx + 1].repeat == p.repeat:
                            p_rec = phases[idx + 1]
                            phases[idx + 1] = WorkoutPhase(
                                name=p_rec.name,
                                duration_min=p_rec.duration_min,
                                zone=p_rec.zone,
                                target_power_pct=p_rec.target_power_pct,
                                target_hr_zone=p_rec.target_hr_zone,
                                target_cadence_rpm=p_rec.target_cadence_rpm,
                                description=p_rec.description,
                                repeat=new_repeat,
                            )
                        remaining_to_reduce -= saved_min
                        if remaining_to_reduce <= 0.5:
                            break

    elif diff < 0:
        # Workout is TOO SHORT. Add `abs(diff)` to the last phase (Cooldown or Endurance)
        needed_min = abs(diff)
        target_idx = len(phases) - 1
        p = phases[target_idx]
        phases[target_idx] = WorkoutPhase(
            name=p.name,
            duration_min=round(p.duration_min + (needed_min / max(1, p.repeat)), 1),
            zone=p.zone,
            target_power_pct=p.target_power_pct,
            target_hr_zone=p.target_hr_zone,
            target_cadence_rpm=p.target_cadence_rpm,
            description=p.description,
            repeat=p.repeat,
        )

    candidate.phases = phases
    return candidate
