"""Shared enums/constants used across schemas, services, and coaching agents."""

from enum import StrEnum


class Sport(StrEnum):
    CYCLING = "cycling"
    RUNNING = "running"
    SWIMMING = "swimming"
    CROSS_COUNTRY_SKIING = "cross_country_skiing"
    WEIGHT_TRAINING = "weight_training"


SPORT_PATTERN = "^(" + "|".join(s.value for s in Sport) + ")$"

# Sports with a continuous training-zone model (duration + intensity target).
# Weight training is structured as exercises/sets/reps/RPE instead — see
# services/workout_formatter.py's strength-plan branch.
ENDURANCE_SPORTS = {Sport.CYCLING, Sport.RUNNING, Sport.SWIMMING, Sport.CROSS_COUNTRY_SKIING}
