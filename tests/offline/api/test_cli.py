"""Standard-library tests: no environment setup, device connection or SDK required."""

import json
import os
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

from agile_nero.contracts.drawing import digest
from tests.offline.support import EXAMPLE, ROOT, example


class CliTests(unittest.TestCase):
    def test_legacy_cli_matches_canonical_output(self):
        canonical = self.invoke("--input", EXAMPLE)
        legacy = subprocess.run(
            [sys.executable, "-S", "-m", "agile_nero.drawing", "--input", str(EXAMPLE)],
            env={**os.environ, "PYTHONPATH": str(ROOT / "src")},
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=10,
        )
        self.assertEqual(canonical.returncode, 0, canonical.stderr)
        self.assertEqual(legacy.returncode, 0, legacy.stderr)
        self.assertEqual(json.loads(canonical.stdout), json.loads(legacy.stdout))

    def invoke(self, *args):
        env = {**os.environ, "PYTHONPATH": str(ROOT / "src")}
        return subprocess.run(
            [sys.executable, "-S", "-m", "agile_nero.api", *map(str, args)],
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
             "agile_nero.transport", "agile_nero.state", "agile_nero.cli",
             "agile_nero.commission", "agile_nero.robot.diagnostics", "agile_nero.drawing"}
class BlockImports(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if any(fullname == name or fullname.startswith(name + ".") for name in forbidden):
            raise AssertionError("Forbidden import: " + fullname)
sys.meta_path.insert(0, BlockImports())
sys.argv = ["nero-dry-run", "--input", sys.argv[1]]
runpy.run_module("agile_nero.api", run_name="__main__")
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
