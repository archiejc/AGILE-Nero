"""Independent geometric checks; passing does not authorize physical execution."""

import math
from dataclasses import asdict, dataclass

from agile_nero.contracts.drawing import Action, Toolpath


@dataclass(frozen=True)
class ValidationReport:
    path_sha256: str
    issues: tuple[str, ...]
    scope: str = "drawing_geometry"

    @property
    def passed(self) -> bool:
        return not self.issues

    def to_dict(self) -> dict:
        return {**asdict(self), "issues": list(self.issues), "passed": self.passed}


def validate_path(path: Toolpath) -> ValidationReport:
    points = path.waypoints
    config = path.config
    issues = []
    if not points or len(points) > config.max_waypoints:
        issues.append("Path must be nonempty and within max_waypoints")
    if points and (points[0].action != Action.START or points[-1].action != Action.LIFT):
        issues.append("Path must start above the first stroke and end with a lift")
    transitions = {
        Action.START: {Action.LOWER},
        Action.TRAVEL: {Action.LOWER},
        Action.LOWER: {Action.DRAW},
        Action.DRAW: {Action.DRAW, Action.LIFT},
        Action.LIFT: {Action.TRAVEL},
    }
    seen = set()
    for index, point in enumerate(points):
        prefix = f"Waypoint {index}: "
        if not (0 <= point.x <= config.width_mm and 0 <= point.y <= config.height_mm):
            issues.append(prefix + "outside workspace")
        expected_z = 0 if point.action in (Action.LOWER, Action.DRAW) else config.lift_mm
        if point.z != expected_z:
            issues.append(prefix + "incorrect pen height")
        if point.action in (Action.START, Action.TRAVEL):
            if point.stroke_id in seen:
                issues.append(prefix + "stroke id reused")
            seen.add(point.stroke_id)
        if index == 0:
            continue
        previous = points[index - 1]
        if point.action not in transitions[previous.action]:
            issues.append(prefix + "invalid pen-state transition")
        if point.action != Action.TRAVEL and point.stroke_id != previous.stroke_id:
            issues.append(prefix + "stroke changed without lift and travel")
        if point.action in (Action.LOWER, Action.LIFT) and (point.x, point.y) != (
            previous.x,
            previous.y,
        ):
            issues.append(prefix + "pen transition must be vertical")
        if point.action == Action.DRAW:
            length = math.dist(previous.xyz, point.xyz)
            if (
                not math.isfinite(length)
                or length == 0
                or length / config.max_draw_segment_mm > 1 + 1e-9
            ):
                issues.append(prefix + "invalid drawing segment length")
    return ValidationReport(path.sha256, tuple(issues))
