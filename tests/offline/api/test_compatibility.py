"""Preserve public import identity after moving implementations into modules."""

import importlib
import unittest


class CompatibilityTests(unittest.TestCase):
    def test_public_symbols_are_the_canonical_objects(self):
        mappings = (
            ("models", "contracts.drawing", ("DrawingTask", "Toolpath", "Point2D", "Stroke")),
            ("planning", "planning.planar", ("plan_task",)),
            ("validation", "planning.validation", ("ValidationReport", "validate_path")),
            ("workflow", "workflow.offline", ("WorkflowResult", "run_task", "run_tool")),
            ("ports", "simulation.ports", ("PreviewBackend", "PreviewReport")),
            ("ports", "robot.ports", ("RobotBackend", "UnadaptedRobotBackend")),
            ("preview", "simulation.offline", ("OfflinePreviewBackend",)),
            ("preview", "artifacts.svg", ("render_svg",)),
            ("preview", "planning.metrics", ("path_metrics",)),
            ("cli", "api.cli", ("main",)),
        )
        for legacy, canonical, symbols in mappings:
            before = importlib.import_module("agile_nero.drawing." + legacy)
            after = importlib.import_module("agile_nero." + canonical)
            for symbol in symbols:
                with self.subTest(symbol=symbol):
                    self.assertIs(getattr(before, symbol), getattr(after, symbol))
