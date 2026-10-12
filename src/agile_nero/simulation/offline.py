"""Offline geometric preview, independent of physics engines."""

from agile_nero.contracts.drawing import Toolpath
from agile_nero.planning.validation import validate_path
from agile_nero.simulation.ports import PreviewReport


class OfflinePreviewBackend:
    def preview(self, path: Toolpath) -> PreviewReport:
        report = validate_path(path)
        return PreviewReport(
            "offline",
            "drawing_geometry",
            path.sha256,
            report.passed,
            (
                "Planar bounds, sampling and pen transitions checked",
                "Robot simulation, calibration and physical execution pending",
            ),
        )
