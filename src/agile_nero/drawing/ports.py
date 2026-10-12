"""Adapter contracts. The offline workflow has no robot backend parameter."""

from dataclasses import asdict, dataclass
from typing import Protocol

from agile_nero.drawing.models import Toolpath, identifier


@dataclass(frozen=True)
class PreviewReport:
    backend: str
    scope: str
    path_sha256: str
    passed: bool
    details: tuple[str, ...] = ()

    def __post_init__(self):
        identifier(self.backend, "backend")
        identifier(self.scope, "scope")
        if type(self.passed) is not bool or not isinstance(self.path_sha256, str):
            raise ValueError("Preview result requires a boolean passed and a string digest")
        object.__setattr__(self, "details", tuple(self.details))
        if not all(isinstance(detail, str) for detail in self.details):
            raise ValueError("Preview details must be strings")

    def to_dict(self) -> dict:
        return {**asdict(self), "details": list(self.details)}


class PreviewBackend(Protocol):
    """A future MuJoCo adapter returns model-specific evidence for this exact path."""

    def preview(self, path: Toolpath) -> PreviewReport: ...


class RobotBackend(Protocol):
    """Reserved SDK boundary; adapting geometry requires separate commissioning."""

    def execute(self, path: Toolpath) -> None: ...


class UnadaptedRobotBackend:
    """A fail-closed placeholder; no SDK import, device connection or motion API."""

    def execute(self, path: Toolpath) -> None:
        raise RuntimeError("Physical execution unavailable: robot adapter is unadapted")
