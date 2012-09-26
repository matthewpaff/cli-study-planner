"""Validation shared by commands and data import."""
from datetime import date

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


def validate_due(value):
    if value is None:
        return None
    try:
        parsed = date.fromisoformat(value)
        if parsed.isoformat() != value:
            raise ValueError
    except (ValueError, TypeError):
        raise PlannerError("Due date must be a valid YYYY-MM-DD date")
    return value
