"""Offline drawing preview. Never imports diagnostics, USB/CAN, SDKs or agent frameworks."""

import argparse
import json
import sys
from pathlib import Path

from agile_nero.drawing.models import DrawingTask
from agile_nero.drawing.preview import render_svg
from agile_nero.drawing.workflow import run_task

MAX_INPUT_BYTES = 1_000_000


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate JSON field: {key}")
        result[key] = value
    return result


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path, help="Version 1 drawing-task JSON")
    parser.add_argument("--output-dir", type=Path, help="New directory for JSON and SVG artifacts")
    args = parser.parse_args(argv)
    try:
        # Bound reads before JSON parsing; this also catches files growing after stat().
        with args.input.open("rb") as stream:
            raw = stream.read(MAX_INPUT_BYTES + 1)
        if len(raw) > MAX_INPUT_BYTES:
            raise ValueError(f"Input exceeds {MAX_INPUT_BYTES} bytes")
        payload = json.loads(raw, object_pairs_hook=unique_object)
        result = run_task(DrawingTask.from_dict(payload))
        report = result.to_dict()
        if args.output_dir and result.status == "previewed":
            path_json = json.dumps(result.path.to_dict(), indent=2, allow_nan=False) + "\n"
            report_json = json.dumps(report, indent=2, allow_nan=False) + "\n"
            svg = render_svg(result.path)
            # A new directory prevents old previews being mistaken for the current run.
            args.output_dir.mkdir(parents=True, exist_ok=False)
            (args.output_dir / "toolpath.json").write_text(path_json, encoding="utf-8")
            (args.output_dir / "preview.svg").write_text(svg, encoding="utf-8")
            (args.output_dir / "report.json").write_text(report_json, encoding="utf-8")
    except (OSError, ValueError, RecursionError) as exc:
        report = {
            "schema_version": 1,
            "status": "rejected",
            "stages": ["rejected"],
            "physical_execution": "unavailable",
            "robot_adapter": "unadapted",
            "error": f"{type(exc).__name__}: {exc}",
        }
    print(json.dumps(report, indent=2, allow_nan=False))
    return 0 if report["status"] == "previewed" else 1


if __name__ == "__main__":
    sys.exit(main())
