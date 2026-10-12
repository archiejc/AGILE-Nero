"""Standard-library tests: no environment setup, device connection or SDK required."""

import json
import unittest
from dataclasses import replace

from agile_nero.contracts.drawing import DrawingTask, Point2D
from agile_nero.simulation.ports import PreviewReport
from agile_nero.workflow.offline import run_task, run_tool
from tests.offline.support import example


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.task = DrawingTask.from_dict(example())

    def test_success_reports_geometry_and_unavailable_hardware(self):
        report = run_task(self.task).to_dict()
        self.assertEqual(report["status"], "previewed")
        self.assertEqual(report["stages"], ["planned", "validated", "previewed"])
        self.assertEqual(report["preview"]["scope"], "drawing_geometry")
        self.assertEqual(report["preview"]["path_sha256"], report["path_sha256"])
        self.assertEqual(report["physical_execution"], "unavailable")
        self.assertEqual(report["robot_adapter"], "unadapted")
        json.dumps(report, allow_nan=False)

    def test_overflowing_metrics_are_rejected_as_json(self):
        payload = example()
        payload["workspace"] = {"width_mm": 1e308, "height_mm": 1}
        payload["planning"].update(lift_mm=1, max_draw_segment_mm=1e308)
        payload["strokes"] = [{"id": "long", "points": [[0, 0], [1e308, 0], [0, 0]]}]
        report = run_tool(payload)
        self.assertEqual(report["status"], "rejected")
        json.dumps(report, allow_nan=False)

    def test_alternate_preview_backend_can_be_injected(self):
        class FakeSimulation:
            def preview(self, path):
                return PreviewReport("test-double", "test_only", path.sha256, True)

        result = run_task(self.task, preview_backend=FakeSimulation())
        self.assertEqual(result.preview.backend, "test-double")
        self.assertEqual(result.to_dict()["physical_execution"], "unavailable")

    def test_failed_stale_and_exceptional_previews_are_rejected(self):
        class FakePreview:
            def __init__(self, mode):
                self.mode = mode

            def preview(self, path):
                if self.mode == "error":
                    raise RuntimeError("test failure")
                if self.mode == "wrong_type":
                    return {"passed": True}
                return PreviewReport(
                    "test-double",
                    "test_only",
                    "0" * 64 if self.mode == "stale" else path.sha256,
                    self.mode != "failed",
                )

        for mode in ("failed", "stale", "error", "wrong_type"):
            with self.subTest(mode=mode):
                result = run_task(self.task, preview_backend=FakePreview(mode))
                self.assertEqual(result.status, "rejected")
                self.assertIsNotNone(result.error)

    def test_invalid_input_does_not_reach_backend(self):
        class MustNotRun:
            def preview(self, path):
                self.fail = True
                raise AssertionError("backend called")

        bad_stroke = replace(self.task.strokes[0], points=(Point2D(-1, 0), Point2D(1, 1)))
        backend = MustNotRun()
        with self.assertRaises(ValueError):
            run_task(replace(self.task, strokes=(bad_stroke,)), preview_backend=backend)
        self.assertFalse(hasattr(backend, "fail"))
