"""Standard-library tests: no environment setup, device connection or SDK required."""

import unittest
import xml.etree.ElementTree as ET
from dataclasses import replace

from agile_nero.artifacts.svg import render_svg
from agile_nero.contracts.drawing import DrawingTask
from agile_nero.planning.planar import plan_task
from tests.offline.support import example


class SvgTests(unittest.TestCase):
    def setUp(self):
        self.task = DrawingTask.from_dict(example())
        self.path = plan_task(self.task)

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
