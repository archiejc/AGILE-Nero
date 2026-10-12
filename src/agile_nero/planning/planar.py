"""Preserve stroke order and sample planar drawing segments without robot kinematics."""

import math

from agile_nero.contracts.drawing import Action, DrawingTask, Toolpath, Waypoint, digest


def plan_task(task: DrawingTask) -> Toolpath:
    config = task.config
    for stroke in task.strokes:
        for point in stroke.points:
            if not (0 <= point.x <= config.width_mm and 0 <= point.y <= config.height_mm):
                raise ValueError(f"Stroke {stroke.id!r} leaves the drawing workspace")

    waypoints = []

    def append(x, y, z, action, stroke_id):
        if len(waypoints) >= config.max_waypoints:
            raise ValueError("Toolpath exceeds max_waypoints; increase sampling distance")
        waypoints.append(Waypoint(x, y, z, action, stroke_id))

    for stroke in task.strokes:
        first = stroke.points[0]
        append(
            first.x,
            first.y,
            config.lift_mm,
            Action.START if not waypoints else Action.TRAVEL,
            stroke.id,
        )
        append(first.x, first.y, 0, Action.LOWER, stroke.id)
        for start, end in zip(stroke.points, stroke.points[1:]):
            length = math.hypot(end.x - start.x, end.y - start.y)
            if length == 0:
                continue
            ratio = length / config.max_draw_segment_mm
            # Check before ceil/allocation, including infinite ratios from tiny sample sizes.
            if ratio > config.max_waypoints - len(waypoints) - 1:
                raise ValueError("Toolpath exceeds max_waypoints; increase sampling distance")
            count = max(1, math.ceil(ratio))
            for index in range(1, count + 1):
                t = index / count
                x = end.x if index == count else start.x + (end.x - start.x) * t
                y = end.y if index == count else start.y + (end.y - start.y) * t
                append(x, y, 0, Action.DRAW, stroke.id)
        last = stroke.points[-1]
        append(last.x, last.y, config.lift_mm, Action.LIFT, stroke.id)
    return Toolpath(task.task_id, digest(task.to_dict()), config, tuple(waypoints))
