"""Environment and hardware diagnostics, with no motor-control commands."""

import argparse
import importlib.metadata
import json
import math
import platform
import sys
import time
import tomllib
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from agile_nero.robot.diagnostics.transport import NativeGsUsbBus, devices


def device_report():
    return [
        {
            "product": d.gs_usb.product,
            "serial": d.serial_number,
            "vid": f"0x{d.gs_usb.idVendor:04X}",
            "pid": f"0x{d.gs_usb.idProduct:04X}",
        }
        for d in devices()
    ]


def doctor():
    import cv2
    import mujoco
    import numpy as np
    from scipy.interpolate import CubicSpline
    from skimage.morphology import skeletonize
    from svgpathtools import parse_path

    packages = (
        "pyAgxArm",
        "python-can",
        "gs-usb",
        "pyusb",
        "numpy",
        "scipy",
        "opencv-python-headless",
        "scikit-image",
        "svgpathtools",
        "mujoco",
    )
    checks = {}
    image = np.zeros((32, 32), dtype=np.uint8)
    cv2.line(image, (4, 4), (27, 27), 255, 3)
    checks["opencv_skeleton"] = bool(skeletonize(image > 0).sum() > 0)
    checks["svg_path"] = math.isclose(parse_path("M0,0 L10,0").length(), 10)
    spline = CubicSpline([0, 1, 2], [0, 1, 0])
    checks["scipy_spline"] = bool(np.isfinite(spline(np.linspace(0, 2, 20))).all())
    model = mujoco.MjModel.from_xml_string(
        '<mujoco><worldbody><body pos="0 0 1"><freejoint/>'
        '<geom type="sphere" size="0.05" mass="1"/></body></worldbody></mujoco>'
    )
    data = mujoco.MjData(model)
    for _ in range(10):
        mujoco.mj_step(model, data)
    checks["mujoco_physics"] = bool(data.time > 0 and np.isfinite(data.qpos).all())
    with mujoco.Renderer(model, height=64, width=64) as renderer:
        renderer.update_scene(data)
        pixels = renderer.render()
    checks["mujoco_render"] = bool(pixels.shape == (64, 64, 3) and pixels.std() > 0)
    optional = {}
    try:
        import torch
        import torchvision

        available = torch.backends.mps.is_available()
        optional["torch"] = torch.__version__
        optional["torchvision"] = torchvision.__version__
        optional["mps_available"] = available
        if available:
            x = torch.ones((16, 16), device="mps")
            checks["mps_matmul"] = float((x @ x).sum().cpu()) == 4096
    except ImportError:
        optional["ml"] = "not installed; uv sync --extra ml"
    try:
        from langgraph.graph import END, START, StateGraph

        graph = StateGraph(dict)
        graph.add_node("check", lambda state: {"ready": True})
        graph.add_edge(START, "check")
        graph.add_edge("check", END)
        checks["langgraph_execution"] = graph.compile().invoke({})["ready"]
        optional["langgraph"] = importlib.metadata.version("langgraph")
    except ImportError:
        optional["workflow"] = "not installed; uv sync --extra workflow"
    return {
        "python": platform.python_version(),
        "architecture": platform.machine(),
        "platform": platform.platform(),
        "packages": {p: importlib.metadata.version(p) for p in packages},
        "optional": optional,
        "checks": checks,
        "usb_adapters": device_report(),
        "passed": all(checks.values()),
        "scope": "environment smoke checks; NERO simulation/calibration are separate",
    }


def listen(channel, bitrate, seconds):
    with NativeGsUsbBus(channel=channel, bitrate=bitrate) as bus:
        started = time.monotonic()
        while time.monotonic() - started < seconds:
            bus.recv(timeout=max(0.001, min(0.1, seconds - (time.monotonic() - started))))
        return {
            "duration_s": round(time.monotonic() - started, 3),
            "receive_counts": dict(sorted(bus.rx_counts.items())),
            "error_frames": bus.rx_error_frames,
            "transmitted_can_frames": bus.tx_firmware_queries,
            "passed": bool(bus.rx_counts) and bus.rx_error_frames == 0,
        }


def serialize(value):
    if value is None:
        return None
    if hasattr(value, "msg"):
        return {"value": serialize(value.msg), "timestamp": value.timestamp, "hz": value.hz}
    if isinstance(value, dict):
        return {str(k): serialize(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [serialize(v) for v in value]
    if isinstance(value, (str, int, float, bool)):
        return value
    if hasattr(value, "__dict__"):
        return {k: serialize(v) for k, v in vars(value).items()}
    return str(value)


def read_state(channel, bitrate, seconds, known_firmware=None):
    import can
    from pyAgxArm import ArmModel, resolve_firmware_profile

    from agile_nero.robot.diagnostics.state import StateDecoder, decode_firmware

    firmware_source = "user-supplied" if known_firmware else "device-query"
    firmware = {"software_version": known_firmware} if known_firmware else None
    if firmware:
        resolve_firmware_profile(ArmModel.NERO, known_firmware)
    with NativeGsUsbBus(channel=channel, bitrate=bitrate) as bus:
        if firmware is None:
            bus.send(can.Message(arbitration_id=0x4AF, data=[1], is_extended_id=False))
            deadline = time.monotonic() + 3.0
            while time.monotonic() < deadline and firmware is None:
                firmware = decode_firmware(bus.recv(timeout=0.1))
            if firmware is None:
                return {
                    "passed": False,
                    "reason": "Firmware query returned no response",
                    "receive_counts": dict(bus.rx_counts),
                    "firmware_query_frames": bus.tx_firmware_queries,
                    "motion_frames_sent": 0,
                    "suggestion": "Verify CAN feedback and retry. If actual firmware is "
                    "known from the web UI, use --firmware VERSION.",
                }
        profile = resolve_firmware_profile(ArmModel.NERO, firmware["software_version"])
        decoder = StateDecoder(profile)
        try:
            started = time.monotonic()
            while time.monotonic() - started < seconds:
                message = bus.recv(timeout=0.1)
                if message is not None:
                    decoder.feed(message)
            snapshot = decoder.snapshot()
            result = serialize(snapshot)
            result.update(
                {
                    "firmware": firmware,
                    "firmware_source": firmware_source,
                    "firmware_profile": profile,
                    "receive_counts": dict(sorted(bus.rx_counts.items())),
                    "duration_s": round(time.monotonic() - started, 3),
                    "error_frames": bus.rx_error_frames,
                    "firmware_query_frames": bus.tx_firmware_queries,
                    "motion_frames_sent": 0,
                    "passed": snapshot["joint_feedback_fresh"] and bus.rx_error_frames == 0,
                    "scope": "Feedback decoding; motion, TCP and trajectories are unvalidated",
                }
            )
            return result
        finally:
            decoder.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for command in ("doctor", "devices", "listen", "read-state"):
        p = sub.add_parser(command)
        p.add_argument("--output", type=Path)
        if command in ("listen", "read-state"):
            p.add_argument("--config", type=Path, default=Path("configs/robot.example.toml"))
            p.add_argument("--serial", help="USB adapter serial number")
            p.add_argument("--bitrate", type=int)
            p.add_argument("--seconds", type=float, default=5)
        if command == "read-state":
            p.add_argument("--firmware", help="Actual firmware from web UI, e.g. 1.20")
    args = parser.parse_args()
    try:
        if args.command == "doctor":
            result = doctor()
        elif args.command == "devices":
            result = {"adapters": device_report()}
        else:
            if not math.isfinite(args.seconds) or not 0 < args.seconds <= 60:
                raise ValueError("--seconds must be between 0 and 60")
            config = tomllib.loads(args.config.read_text()) if args.config.exists() else {}
            channel = args.serial or config.get("adapter_serial", "auto")
            bitrate = args.bitrate or config.get("bitrate", 1_000_000)
            if args.command == "listen":
                result = listen(channel, bitrate, args.seconds)
            else:
                result = read_state(channel, bitrate, args.seconds, args.firmware)
        result["checked_at"] = datetime.now(ZoneInfo("Asia/Shanghai")).isoformat()
    except Exception as exc:
        result = {"passed": False, "error": f"{type(exc).__name__}: {exc}"}
    output = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(output + "\n")
    print(output)
    return 1 if result.get("passed") is False else 0


if __name__ == "__main__":
    sys.exit(main())
