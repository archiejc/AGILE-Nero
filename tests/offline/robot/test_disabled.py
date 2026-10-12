"""Standard-library tests: no environment setup, device connection or SDK required."""

import unittest

from agile_nero.contracts.drawing import DrawingTask
from agile_nero.planning.planar import plan_task
from agile_nero.robot.ports import UnadaptedRobotBackend
from tests.offline.support import example


class DisabledRobotTests(unittest.TestCase):
    def setUp(self):
        self.task = DrawingTask.from_dict(example())

    def test_robot_placeholder_always_blocks_execution(self):
        with self.assertRaisesRegex(RuntimeError, "Physical execution unavailable"):
            UnadaptedRobotBackend().execute(plan_task(self.task))
