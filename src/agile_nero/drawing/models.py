"""Compatibility exports only; add new code to the domain module."""

from agile_nero.contracts.drawing import (
    MAX_INPUT_POINTS,
    MAX_WAYPOINTS,
    Action,
    DrawingTask,
    PlanningConfig,
    Point2D,
    Stroke,
    Toolpath,
    digest,
    fields,
    identifier,
    number,
)

__all__ = [
    "MAX_INPUT_POINTS",
    "MAX_WAYPOINTS",
    "Action",
    "DrawingTask",
    "PlanningConfig",
    "Point2D",
    "Stroke",
    "Toolpath",
    "digest",
    "fields",
    "identifier",
    "number",
]
