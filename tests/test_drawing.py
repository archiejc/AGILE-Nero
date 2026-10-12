"""Standard-library tests: no environment setup, device connection or SDK required."""

import json
import math
import os
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from dataclasses import FrozenInstanceError, replace
from pathlib import Path

from agile_nero.drawing.models import Action, DrawingTask, Point2D, digest
from agile_nero.drawing.planning import plan_task
from agile_nero.drawing.ports import PreviewReport, UnadaptedRobotBackend
from agile_nero.drawing.preview import path_metrics, render_svg
from agile_nero.drawing.validation import validate_path
from agile_nero.drawing.workflow import run_task, run_tool

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "examples/drawing/two-strokes.json"


def example():
    return json.loads(EXAMPLE.read_text(encoding="utf-8"))


class TaskContractTests(unittest.TestCase):
    def test_non_json_keys_and_control_characters_in_ids_are_rejected(self):
        self.assertEqual(run_tool({1: "invalid"})["status"], "rejected")
        payload = example()
        payload["task_id"] = "invalid\u0000label"
        self.assertEqual(run_tool(payload)["status"], "rejected")

    def test_normalized_round_trip_and_immutable_points(self):
        task = DrawingTask.from_dict(example())
        self.assertEqual(DrawingTask.from_dict(task.to_dict()), task)
        with self.assertRaises(FrozenInstanceError):
            task.strokes[0].points[0].x = 2

    def test_units_frame_version_and_unknown_fields_are_rejected(self):
        changes = [
            {"units": "m"},
            {"frame": "robot_base"},
            {"schema_version": 2},
            {"schema_version": True},
            {"backend": "hardware"},
            {"strokes": []},
        ]
        for change in changes:
            with self.subTest(change=change):
                report = run_tool({**example(), **change})
                self.assertEqual(report["status"], "rejected")
                self.assertEqual(report["physical_execution"], "unavailable")

    def test_nonfinite_and_boolean_coordinates_are_rejected(self):
        for value in (float("nan"), float("inf"), float("-inf"), True, "10", 10**400):
            with self.subTest(value=str(value)):
                payload = example()
                payload["strokes"][0]["points"][0][0] = value
                self.assertEqual(run_tool(payload)["status"], "rejected")

    def test_malformed_and_degenerate_strokes_are_rejected(self):
        for points in ([[0, 0]], [[0, 0], [0, 0]], [[0, 0, 0], [1, 1]], "invalid"):
            with self.subTest(points=points):
                payload = example()
                payload["strokes"][0]["points"] = points
                self.assertEqual(run_tool(payload)["status"], "rejected")
        payload = example()
        payload["strokes"][1]["id"] = payload["strokes"][0]["id"]
        self.assertEqual(run_tool(payload)["status"], "rejected")

    def test_invalid_configuration_is_rejected(self):
        for change in (
            {"lift_mm": 0},
            {"lift_mm": -1},
            {"max_draw_segment_mm": 0},
            {"max_waypoints": True},
            {"max_waypoints": 1.5},
            {"max_waypoints": 100001},
            {"robot_ip": "127.0.0.1"},
        ):
            with self.subTest(change=change):
                payload = example()
                payload["planning"].update(change)
                self.assertEqual(run_tool(payload)["status"], "rejected")

    def test_input_point_limit_is_enforced(self):
        payload = example()
        payload["strokes"][0]["points"] = [[0, 0], [1, 1]] * 5001
        self.assertEqual(run_tool(payload)["status"], "rejected")


class PlanningTests(unittest.TestCase):
    def setUp(self):
        self.task = DrawingTask.from_dict(example())
        self.path = plan_task(self.task)

    def test_expected_length_sampling_and_pen_transitions(self):
        self.assertTrue(validate_path(self.path).passed)
        self.assertEqual(len(self.path.waypoints), 51)
        self.assertEqual(self.path.waypoints[0].xyz, (10, 10, 5))
        self.assertEqual(self.path.waypoints[1].xyz, (10, 10, 0))
        travel_index = next(
            i for i, p in enumerate(self.path.waypoints) if p.action == Action.TRAVEL
        )
        self.assertEqual(self.path.waypoints[travel_index - 1].action, Action.LIFT)
        self.assertEqual(self.path.waypoints[travel_index].xyz, (60, 20, 5))
        self.assertEqual(self.path.waypoints[travel_index + 1].action, Action.LOWER)
        self.assertEqual(self.path.waypoints[-1].xyz, (80, 40, 5))
        metrics = path_metrics(self.path)
        self.assertAlmostEqual(metrics["draw_length_mm"], 60 + math.sqrt(800))
        self.assertAlmostEqual(metrics["non_drawing_length_mm"], 20 + math.sqrt(800))
        self.assertEqual(metrics["stroke_count"], 2)

    def test_closed_strokes_and_repeated_adjacent_points(self):
        payload = example()
        payload["strokes"] = [{"id": "loop", "points": [[0, 0], [0, 0], [2, 0], [0, 0]]}]
        path = plan_task(DrawingTask.from_dict(payload))
        self.assertTrue(validate_path(path).passed)
        self.assertEqual(path_metrics(path)["draw_length_mm"], 4)
        self.assertEqual(path.waypoints[-1].xyz, (0, 0, 5))

    def test_out_of_bounds_and_sampling_explosion_are_rejected(self):
        payload = example()
        payload["strokes"][0]["points"][0][0] = -0.1
        self.assertEqual(run_tool(payload)["status"], "rejected")
        payload = example()
        payload["strokes"][1]["points"][-1][1] = 80.1
        self.assertEqual(run_tool(payload)["status"], "rejected")
        payload = example()
        payload["planning"]["max_draw_segment_mm"] = 1e-300
        self.assertEqual(run_tool(payload)["status"], "rejected")

    def test_waypoint_budget_includes_pen_events(self):
        config = replace(self.task.config, max_waypoints=51)
        self.assertEqual(len(plan_task(replace(self.task, config=config)).waypoints), 51)
        with self.assertRaises(ValueError):
            plan_task(replace(self.task, config=replace(config, max_waypoints=50)))

    def test_hash_is_stable_and_binds_source_configuration_and_path(self):
        self.assertEqual(self.path.sha256, plan_task(self.task).sha256)
        self.assertEqual(self.path.source_sha256, digest(self.task.to_dict()))
        changed = replace(self.task, config=replace(self.task.config, lift_mm=6))
        self.assertNotEqual(plan_task(changed).sha256, self.path.sha256)
        moved = replace(self.path.waypoints[2], x=12.5)
        self.assertNotEqual(
            replace(
                self.path, waypoints=(*self.path.waypoints[:2], moved, *self.path.waypoints[3:])
            ).sha256,
            self.path.sha256,
        )

    def test_validator_rejects_tampered_paths(self):
        cases = []
        huge_points = list(self.path.waypoints)
        huge_points[2] = replace(huge_points[2], x=1.79e308, y=1.79e308)
        cases.append(
            replace(
                self.path,
                waypoints=tuple(huge_points),
                config=replace(
                    self.path.config,
                    width_mm=1.79e308,
                    height_mm=1.79e308,
                    max_draw_segment_mm=1.79e308,
                ),
            )
        )
        for index, change in (
            (0, {"action": Action.DRAW}),
            (1, {"x": 11}),
            (2, {"z": 5}),
            (2, {"x": 40}),
            (2, {"stroke_id": "other"}),
            (-1, {"z": 0}),
        ):
            points = list(self.path.waypoints)
            points[index] = replace(points[index], **change)
            cases.append(replace(self.path, waypoints=tuple(points)))
        cases.extend(
            [
                replace(self.path, waypoints=()),
                replace(self.path, waypoints=self.path.waypoints[:-1]),
            ]
        )
        for path in cases:
            with self.subTest(points=len(path.waypoints)):
                self.assertFalse(validate_path(path).passed)
                with self.assertRaises(ValueError):
                    render_svg(path)

    def test_svg_contains_drawing_and_raised_travel_and_escapes_labels(self):
        path = replace(self.path, task_id='<script>&"')
        root = ET.fromstring(render_svg(path))
        lines = root.findall(".//{http://www.w3.org/2000/svg}line")
        self.assertEqual(len(lines), 46)
        self.assertEqual(sum("stroke-dasharray" in line.attrib for line in lines), 1)
        self.assertEqual(
            root.find("{http://www.w3.org/2000/svg}title").text,
            '<script>&": offline drawing-plane preview',
        )
        self.assertEqual(lines[0].attrib["y1"], "70")


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

    def test_robot_placeholder_always_blocks_execution(self):
        with self.assertRaisesRegex(RuntimeError, "Physical execution unavailable"):
            UnadaptedRobotBackend().execute(plan_task(self.task))


class CliTests(unittest.TestCase):
    def invoke(self, *args):
        env = {**os.environ, "PYTHONPATH": str(ROOT / "src")}
        return subprocess.run(
            [sys.executable, "-S", "-m", "agile_nero.drawing", *map(str, args)],
            env=env,
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=10,
        )

    def test_cli_without_site_packages_emits_consistent_artifacts(self):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / "run"
            result = self.invoke("--input", EXAMPLE, "--output-dir", output)
            self.assertEqual(result.returncode, 0, result.stderr)
            report = json.loads(result.stdout)
            saved_report = json.loads((output / "report.json").read_text())
            self.assertEqual(report, saved_report)
            self.assertEqual(
                digest(json.loads((output / "toolpath.json").read_text())),
                saved_report["path_sha256"],
            )
            ET.fromstring((output / "preview.svg").read_text())
            original = {p.name: p.read_bytes() for p in output.iterdir()}
            repeated = self.invoke("--input", EXAMPLE, "--output-dir", output)
            self.assertEqual(repeated.returncode, 1)
            self.assertEqual({p.name: p.read_bytes() for p in output.iterdir()}, original)

    def test_cli_rejects_invalid_duplicate_and_oversized_input_without_artifacts(self):
        payload = example()
        payload["units"] = "m"
        bodies = [
            "[" * 2000 + "]" * 2000,
            json.dumps(payload),
            '{"task_id":"a","task_id":"b"}',
            "[1, 2]",
            "{" + " " * 1_000_000,
        ]
        for body in bodies:
            with self.subTest(size=len(body)), tempfile.TemporaryDirectory() as folder:
                source, output = Path(folder) / "task.json", Path(folder) / "run"
                source.write_text(body)
                result = self.invoke("--input", source, "--output-dir", output)
                self.assertEqual(result.returncode, 1, result.stderr)
                self.assertEqual(json.loads(result.stdout)["status"], "rejected")
                self.assertFalse(output.exists())

    def test_cli_imports_no_hardware_simulator_or_framework_modules(self):
        code = """
import importlib.abc
import json
import runpy
import sys
forbidden = {"can", "usb", "gs_usb", "pyAgxArm", "mujoco", "langgraph", "torch", "cv2",
             "agile_nero.transport", "agile_nero.state", "agile_nero.cli", "agile_nero.commission"}
class BlockImports(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if any(fullname == name or fullname.startswith(name + ".") for name in forbidden):
            raise AssertionError("Forbidden import: " + fullname)
sys.meta_path.insert(0, BlockImports())
sys.argv = ["nero-dry-run", "--input", sys.argv[1]]
runpy.run_module("agile_nero.drawing", run_name="__main__")
"""
        result = subprocess.run(
            [sys.executable, "-S", "-c", code, str(EXAMPLE)],
            env={**os.environ, "PYTHONPATH": str(ROOT / "src")},
            capture_output=True,
            text=True,
            timeout=10,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["status"], "previewed")


if __name__ == "__main__":
    unittest.main()
