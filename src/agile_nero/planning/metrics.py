"""Geometric path lengths; no timing or hardware assumptions."""

import math

from agile_nero.contracts.drawing import Action, Toolpath


def path_metrics(path: Toolpath) -> dict:
    draw_length = 0.0
    travel_length = 0.0
    for previous, point in zip(path.waypoints, path.waypoints[1:]):
        length = math.dist(previous.xyz, point.xyz)
        if point.action == Action.DRAW:
            draw_length += length
        else:
            travel_length += length
    if not math.isfinite(draw_length) or not math.isfinite(travel_length):
        raise ValueError("Path length metrics overflowed")
    return {
        "waypoint_count": len(path.waypoints),
        "stroke_count": sum(p.action == Action.LIFT for p in path.waypoints),
        "draw_length_mm": draw_length,
        "non_drawing_length_mm": travel_length,
    }
