"""Test real SDK decoding, firmware echoes, missing groups and stale feedback."""

import math
import struct

import can
import pytest

from agile_nero.robot.diagnostics.state import StateDecoder, decode_firmware


def frame(ident, data):
    return can.Message(arbitration_id=ident, data=data, is_extended_id=False)


def test_seven_axis_decoding_and_freshness():
    decoder = StateDecoder("v111")
    try:
        for ident, pair in ((0x2A5, (1000, -2000)), (0x2A6, (3000, -4000)), (0x2A7, (5000, -6000))):
            decoder.feed(frame(ident, struct.pack(">ii", *pair)), received_at=10)
        assert decoder.snapshot(now=10)["joint_angles_rad"] is None
        decoder.feed(frame(0x2A9, struct.pack(">ii", 7000, 0)), received_at=10)
        state = decoder.snapshot(now=10)
        assert state["joint_angles_rad"].msg == pytest.approx(
            [math.radians(x) for x in (1, -2, 3, -4, 5, -6, 7)]
        )
        assert state["joint_motors_enabled"] == [None] * 7
        assert decoder.snapshot(now=11.1)["joint_angles_rad"] is None
        assert decoder.context.get_comm() is None
    finally:
        decoder.close()


def test_firmware_reply_and_echo_are_distinct():
    assert decode_firmware(frame(0x4AF, bytes([0, 0, 0, 0, 0, 0, 1, 11]))) == {
        "software_version": "1.11"
    }
    assert decode_firmware(frame(0x4AF, b"\x01")) is None
    assert decode_firmware(frame(0x4AF, b"\x01" + b"\x00" * 7)) is None
    assert decode_firmware(frame(0x2A5, bytes([0, 0, 0, 0, 0, 0, 1, 11]))) is None
