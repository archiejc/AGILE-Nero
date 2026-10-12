"""Standard-library tests: no environment setup, device connection or SDK required."""

import math
import unittest
from dataclasses import replace

from agile_nero.artifacts.svg import render_svg
from agile_nero.contracts.drawing import Action, DrawingTask, digest
from agile_nero.planning.metrics import path_metrics
from agile_nero.planning.planar import plan_task
from agile_nero.planning.validation import validate_path
from agile_nero.workflow.offline import run_tool
from tests.offline.support import example


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
