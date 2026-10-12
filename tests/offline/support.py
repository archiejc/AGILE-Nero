"""Shared deterministic example for offline module tests."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EXAMPLE = ROOT / "examples/drawing/two-strokes.json"


def example():
    return json.loads(EXAMPLE.read_text(encoding="utf-8"))
