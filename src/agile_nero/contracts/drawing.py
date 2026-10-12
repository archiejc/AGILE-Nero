"""Immutable, versioned data contracts in millimetres and drawing-plane coordinates."""

import hashlib
import json
import math
from dataclasses import asdict, dataclass
from enum import StrEnum

MAX_WAYPOINTS = 100_000
MAX_INPUT_POINTS = 10_000


def digest(value: dict) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def number(value, name: str, *, positive: bool = False) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a finite number")
    try:
        result = float(value)
    except OverflowError as exc:
        raise ValueError(f"{name} must be a finite number") from exc
    if not math.isfinite(result) or (positive and result <= 0):
        raise ValueError(f"{name} must be {'positive and ' if positive else ''}finite")
    return result


def identifier(value, name: str) -> str:
    if (
        not isinstance(value, str)
        or not value.strip()
        or not value.isprintable()
        or len(value) > 128
    ):
        raise ValueError(f"{name} must be a nonempty printable string of at most 128 characters")
    return value


def fields(value, required: set[str], optional: set[str] | None = None) -> dict:
    if not isinstance(value, dict):
        raise ValueError("Expected a JSON object")
    if any(not isinstance(key, str) for key in value):
        raise ValueError("Object keys must be strings")
    missing = required - value.keys()
    unknown = value.keys() - required - (optional or set())
    if missing or unknown:
        raise ValueError(f"Invalid fields: missing={sorted(missing)}, unknown={sorted(unknown)}")
    return value


@dataclass(frozen=True)
class Point2D:
    x: float
    y: float

    def __post_init__(self):
        object.__setattr__(self, "x", number(self.x, "x"))
        object.__setattr__(self, "y", number(self.y, "y"))


@dataclass(frozen=True)
class Stroke:
    id: str
    points: tuple[Point2D, ...]

    def __post_init__(self):
        identifier(self.id, "stroke id")
        object.__setattr__(self, "points", tuple(self.points))
        if len(self.points) < 2 or not all(isinstance(p, Point2D) for p in self.points):
            raise ValueError("Each stroke needs at least two Point2D values")
        if all(p == self.points[0] for p in self.points):
            raise ValueError(f"Stroke {self.id!r} has zero length")


@dataclass(frozen=True)
class PlanningConfig:
    width_mm: float
    height_mm: float
    lift_mm: float
    max_draw_segment_mm: float
    max_waypoints: int = 10_000

    def __post_init__(self):
        for name in ("width_mm", "height_mm", "lift_mm", "max_draw_segment_mm"):
            object.__setattr__(self, name, number(getattr(self, name), name, positive=True))
        if type(self.max_waypoints) is not int or not 1 <= self.max_waypoints <= MAX_WAYPOINTS:
            raise ValueError(f"max_waypoints must be an integer between 1 and {MAX_WAYPOINTS}")


@dataclass(frozen=True)
class DrawingTask:
    task_id: str
    config: PlanningConfig
    strokes: tuple[Stroke, ...]

    def __post_init__(self):
        identifier(self.task_id, "task_id")
        if not isinstance(self.config, PlanningConfig):
            raise ValueError("config must be a PlanningConfig")
        object.__setattr__(self, "strokes", tuple(self.strokes))
        if not self.strokes or not all(isinstance(s, Stroke) for s in self.strokes):
            raise ValueError("A drawing task needs at least one Stroke")
        if len({s.id for s in self.strokes}) != len(self.strokes):
            raise ValueError("Stroke ids must be unique")
        if sum(len(s.points) for s in self.strokes) > MAX_INPUT_POINTS:
            raise ValueError(f"Input is limited to {MAX_INPUT_POINTS} points")

    @classmethod
    def from_dict(cls, payload: dict) -> "DrawingTask":
        root = fields(
            payload,
            {"schema_version", "task_id", "units", "frame", "workspace", "planning", "strokes"},
        )
        if type(root["schema_version"]) is not int or root["schema_version"] != 1:
            raise ValueError("Only schema_version=1 is supported")
        if root["units"] != "mm" or root["frame"] != "drawing_plane":
            raise ValueError("Expected units=mm and frame=drawing_plane")
        workspace = fields(root["workspace"], {"width_mm", "height_mm"})
        planning = fields(root["planning"], {"lift_mm", "max_draw_segment_mm"}, {"max_waypoints"})
        if not isinstance(root["strokes"], list):
            raise ValueError("strokes must be a list")
        strokes = []
        count = 0
        for item in root["strokes"]:
            item = fields(item, {"id", "points"})
            if not isinstance(item["points"], list):
                raise ValueError("points must be a list of [x, y] pairs")
            count += len(item["points"])
            if count > MAX_INPUT_POINTS:
                raise ValueError(f"Input is limited to {MAX_INPUT_POINTS} points")
            points = []
            for pair in item["points"]:
                if not isinstance(pair, list) or len(pair) != 2:
                    raise ValueError("Each point must be an [x, y] pair")
                points.append(Point2D(*pair))
            strokes.append(Stroke(item["id"], tuple(points)))
        return cls(root["task_id"], PlanningConfig(**workspace, **planning), tuple(strokes))

    def to_dict(self) -> dict:
        return {
            "schema_version": 1,
            "task_id": self.task_id,
            "units": "mm",
            "frame": "drawing_plane",
            "workspace": {"width_mm": self.config.width_mm, "height_mm": self.config.height_mm},
            "planning": {
                "lift_mm": self.config.lift_mm,
                "max_draw_segment_mm": self.config.max_draw_segment_mm,
                "max_waypoints": self.config.max_waypoints,
            },
            "strokes": [
                {"id": s.id, "points": [[p.x, p.y] for p in s.points]} for s in self.strokes
            ],
        }


class Action(StrEnum):
    START = "start"
    TRAVEL = "travel"
    LOWER = "lower"
    DRAW = "draw"
    LIFT = "lift"


@dataclass(frozen=True)
class Waypoint:
    x: float
    y: float
    z: float
    action: Action
    stroke_id: str

    def __post_init__(self):
        for name in ("x", "y", "z"):
            object.__setattr__(self, name, number(getattr(self, name), name))
        object.__setattr__(self, "action", Action(self.action))
        identifier(self.stroke_id, "stroke_id")

    @property
    def xyz(self) -> tuple[float, float, float]:
        return self.x, self.y, self.z


@dataclass(frozen=True)
class Toolpath:
    task_id: str
    source_sha256: str
    config: PlanningConfig
    waypoints: tuple[Waypoint, ...]

    def __post_init__(self):
        identifier(self.task_id, "task_id")
        if not isinstance(self.config, PlanningConfig):
            raise ValueError("config must be a PlanningConfig")
        object.__setattr__(self, "waypoints", tuple(self.waypoints))
        if not all(isinstance(p, Waypoint) for p in self.waypoints):
            raise ValueError("waypoints must contain Waypoint values")
        if (
            not isinstance(self.source_sha256, str)
            or len(self.source_sha256) != 64
            or any(c not in "0123456789abcdef" for c in self.source_sha256)
        ):
            raise ValueError("source_sha256 must be a SHA-256 hex digest")

    def to_dict(self) -> dict:
        return {
            "schema_version": 1,
            "task_id": self.task_id,
            "source_sha256": self.source_sha256,
            "units": "mm",
            "frame": "drawing_plane",
            "config": asdict(self.config),
            "waypoints": [asdict(p) for p in self.waypoints],
        }

    @property
    def sha256(self) -> str:
        return digest(self.to_dict())
