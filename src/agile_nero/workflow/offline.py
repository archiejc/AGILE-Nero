"""Framework-neutral JSON tool: plan -> validate -> preview, with no execution stage."""

from dataclasses import dataclass

from agile_nero.contracts.drawing import DrawingTask, Toolpath
from agile_nero.planning.metrics import path_metrics
from agile_nero.planning.planar import plan_task
from agile_nero.planning.validation import ValidationReport, validate_path
from agile_nero.simulation.offline import OfflinePreviewBackend
from agile_nero.simulation.ports import PreviewBackend, PreviewReport


@dataclass(frozen=True)
class WorkflowResult:
    status: str
    stages: tuple[str, ...]
    path: Toolpath
    validation: ValidationReport
    preview: PreviewReport | None = None
    error: str | None = None

    def to_dict(self) -> dict:
        return {
            "schema_version": 1,
            "status": self.status,
            "stages": list(self.stages),
            "physical_execution": "unavailable",
            "robot_adapter": "unadapted",
            "toolpath": self.path.to_dict(),
            "path_sha256": self.path.sha256,
            "validation": self.validation.to_dict(),
            "preview": self.preview.to_dict() if self.preview else None,
            "metrics": path_metrics(self.path),
            "error": self.error,
        }


def run_task(task: DrawingTask, *, preview_backend: PreviewBackend | None = None) -> WorkflowResult:
    path = plan_task(task)
    validation = validate_path(path)
    if not validation.passed:
        return WorkflowResult(
            "rejected",
            ("planned", "rejected"),
            path,
            validation,
            error="Geometric validation failed",
        )
    backend = preview_backend if preview_backend is not None else OfflinePreviewBackend()
    try:
        preview = backend.preview(path)
        if not isinstance(preview, PreviewReport):
            raise ValueError("Preview backend must return a PreviewReport")
        if preview.path_sha256 != path.sha256 or preview.passed is not True:
            return WorkflowResult(
                "rejected",
                ("planned", "validated", "rejected"),
                path,
                validation,
                preview,
                "Preview failed or references a different path",
            )
    except Exception as exc:
        return WorkflowResult(
            "rejected",
            ("planned", "validated", "rejected"),
            path,
            validation,
            error=f"Preview failed: {exc}",
        )
    return WorkflowResult(
        "previewed", ("planned", "validated", "previewed"), path, validation, preview
    )


def run_tool(payload: dict) -> dict:
    """Callable by workflow frameworks or a CLI bridge; contains only JSON data."""
    try:
        return run_task(DrawingTask.from_dict(payload)).to_dict()
    except ValueError as exc:
        return {
            "schema_version": 1,
            "status": "rejected",
            "stages": ["rejected"],
            "physical_execution": "unavailable",
            "robot_adapter": "unadapted",
            "error": str(exc),
        }
