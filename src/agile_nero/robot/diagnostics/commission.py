"""Explicitly authorized NERO 1.11 motor enable and feedback setup; no targets."""

import time
from datetime import datetime
from zoneinfo import ZoneInfo

import can
from gs_usb.gs_usb_frame import GsUsbFrame

from agile_nero.robot.diagnostics.state import StateDecoder, decode_firmware
from agile_nero.robot.diagnostics.transport import NativeGsUsbBus

# Exact frames produced by the pinned SDK's v111 enable()/set_normal_mode().
# 0x151 uses MOVE=0xFF (invalid/no movement-mode update), with CAN push=1.
SETUP_FRAMES = {
    (0x471, bytes.fromhex("0802000000000000")): "enable_all_motors",
    (0x470, bytes.fromhex("0000000000000000")): "normal_single_arm_mode",
    (0x151, bytes.fromhex("01ff320000000100")): "enable_can_feedback",
    (0x4AF, b"\x01"): "query_firmware",
}


class FeedbackSetupBus(NativeGsUsbBus):
    """Separate opt-in backend; never broadens the default diagnostics backend."""

    def __init__(self, *args, **kwargs):
        self.tx_records = []
        self.tx_echo_counts = {}
        super().__init__(*args, **kwargs)

    def send(self, msg, timeout=None):
        label = SETUP_FRAMES.get((msg.arbitration_id, bytes(msg.data)))
        if (
            label is None
            or msg.dlc != len(msg.data)
            or msg.is_extended_id
            or msg.is_remote_frame
            or msg.is_error_frame
        ):
            raise can.CanOperationError("Feedback setup rejects motion and unapproved CAN frames")
        record = {
            "id": f"0x{msg.arbitration_id:03X}",
            "data_hex": bytes(msg.data).hex(),
            "purpose": label,
            "sent_at": datetime.now(ZoneInfo("Asia/Shanghai")).isoformat(),
            "usb_write_completed": False,
        }
        self.tx_records.append(record)
        if label == "query_firmware":
            super().send(msg, timeout)
        else:
            self._device.send(GsUsbFrame(can_id=msg.arbitration_id, data=list(msg.data)))
        record["usb_write_completed"] = True

    def _recv_internal(self, timeout):
        message, filtered = super()._recv_internal(timeout)
        if message is not None and not message.is_rx and not message.is_error_frame:
            key = f"0x{message.arbitration_id:03X}"
            self.tx_echo_counts[key] = self.tx_echo_counts.get(key, 0) + 1
        return message, filtered


def enable_feedback(channel, bitrate, seconds, firmware):
    if firmware != "1.11":
        raise ValueError("This reviewed setup sequence supports confirmed NERO firmware 1.11 only")
    from agile_nero.robot.diagnostics.cli import serialize

    decoder = StateDecoder("v111")
    samples = []
    queried_firmware = None
    enabled_at = None
    reason = None
    started = time.monotonic()
    phase = "open_usb"
    bus = None
    try:
        with FeedbackSetupBus(channel=channel, bitrate=bitrate) as bus:
            phase = "motor_enable_and_can_feedback_setup"
            # Bind the pinned SDK encoder to this exact-frame whitelist. No SDK
            # reader thread or second CAN connection is created.
            decoder.robot._send_msg = lambda value: bus.send(decoder.robot._parser.pack(value))
            setup_deadline = time.monotonic() + 8.0
            next_enable = 0.0
            while time.monotonic() < setup_deadline:
                if time.monotonic() >= next_enable:
                    decoder.robot.enable()
                    next_enable = time.monotonic() + 0.5
                message = bus.recv(timeout=0.1)
                if message is not None:
                    decoder.feed(message)
                snapshot = decoder.snapshot()
                status = snapshot["arm_status"]
                if status is not None and (int(status.msg.arm_status) != 0 or status.msg.err_code):
                    reason = "Controller reports non-normal state/error; setup retries stopped"
                    break
                if snapshot["joint_motors_enabled"] == [True] * 7:
                    enabled_at = datetime.now(ZoneInfo("Asia/Shanghai")).isoformat()
                    decoder.robot.set_normal_mode()
                    break
            if enabled_at is None and reason is None:
                reason = "Enable timeout: seven fresh motor-enable confirmations were not received"

            if enabled_at is not None:
                phase = "continuous_state_validation"
                validation_start = time.monotonic()
                next_sample = validation_start + 1.0
                next_query = validation_start
                query_attempts = 0
                while time.monotonic() - validation_start < seconds:
                    if (
                        queried_firmware is None
                        and query_attempts < 3
                        and time.monotonic() >= next_query
                    ):
                        bus.send(can.Message(arbitration_id=0x4AF, data=[1], is_extended_id=False))
                        query_attempts += 1
                        next_query = time.monotonic() + 1.0
                    message = bus.recv(timeout=0.1)
                    if message is not None:
                        decoder.feed(message)
                        reply = decode_firmware(message)
                        if reply is not None:
                            queried_firmware = reply
                    if time.monotonic() >= next_sample:
                        sample = serialize(decoder.snapshot())
                        sample["elapsed_s"] = round(time.monotonic() - validation_start, 3)
                        samples.append(sample)
                        next_sample += 1.0
                samples.append(serialize(decoder.snapshot()))
            final = decoder.snapshot()
            all_fresh = bool(samples) and all(s["joint_feedback_fresh"] for s in samples)
            all_enabled = bool(samples) and all(
                s["joint_motors_enabled"] == [True] * 7 for s in samples
            )
            status = final["arm_status"]
            normal = (
                status is not None and int(status.msg.arm_status) == 0 and status.msg.err_code == 0
            )
            return {
                "passed": enabled_at is not None
                and all_fresh
                and all_enabled
                and normal
                and bus.rx_error_frames == 0,
                "reason": reason,
                "firmware": queried_firmware,
                "configured_firmware": firmware,
                "firmware_profile": "v111",
                "enabled_at": enabled_at,
                "validation_requested_s": seconds,
                "total_duration_s": round(time.monotonic() - started, 3),
                "final_state": serialize(final),
                "samples": samples,
                "receive_counts": dict(sorted(bus.rx_counts.items())),
                "error_frames": bus.rx_error_frames,
                "transmitted_frames": list(bus.tx_records),
                "adapter_tx_echo_counts": dict(bus.tx_echo_counts),
                "motion_target_frames_sent": 0,
                "motor_state_on_exit": serialize(final["joint_motors_enabled"]),
            }
    except Exception as exc:
        return {
            "passed": False,
            "reason": f"{type(exc).__name__}: {exc}",
            "phase": phase,
            "enabled_at": enabled_at,
            "final_state": serialize(decoder.snapshot()),
            "transmitted_frames": list(bus.tx_records) if bus is not None else [],
            "adapter_tx_echo_counts": dict(bus.tx_echo_counts) if bus is not None else {},
            "receive_counts": dict(bus.rx_counts) if bus is not None else {},
            "motion_target_frames_sent": 0,
            "motor_state_on_exit": serialize(decoder.snapshot()["joint_motors_enabled"]),
        }
    finally:
        decoder.close()
