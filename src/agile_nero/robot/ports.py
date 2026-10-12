"""Reserved robot boundary; the placeholder always rejects execution."""

from typing import Protocol

from agile_nero.contracts.drawing import Toolpath


class RobotBackend(Protocol):
    """Reserved SDK boundary; adapting geometry requires separate commissioning."""

    def execute(self, path: Toolpath) -> None: ...


class UnadaptedRobotBackend:
    """A fail-closed placeholder; no SDK import, device connection or motion API."""

    def execute(self, path: Toolpath) -> None:
        raise RuntimeError("Physical execution unavailable: robot adapter is unadapted")
