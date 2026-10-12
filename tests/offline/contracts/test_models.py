"""Standard-library tests: no environment setup, device connection or SDK required."""

import unittest
from dataclasses import FrozenInstanceError

from agile_nero.contracts.drawing import DrawingTask
from agile_nero.workflow.offline import run_tool
from tests.offline.support import example


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
