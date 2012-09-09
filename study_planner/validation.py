"""Validation shared by commands and data import."""

PRIORITIES = ("low", "normal", "high")


class PlannerError(ValueError):
    """An actionable input error that should not produce a traceback."""


def validate_title(value):
    if not isinstance(value, str) or not 1 <= len(value.strip()) <= 200:
        raise PlannerError("Title must contain 1-200 nonblank characters")
    return value.strip()


def validate_priority(value):
    if value not in PRIORITIES:
        raise PlannerError("Priority must be low, normal, or high")
    return value
