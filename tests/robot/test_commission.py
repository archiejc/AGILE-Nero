"""Verify the authorized setup frames match SDK output and reject targets."""

import json
import sys
from unittest.mock import Mock

import can
import pytest

from agile_nero.robot.diagnostics.commission import SETUP_FRAMES, FeedbackSetupBus
from agile_nero.robot.diagnostics.state import StateDecoder


def test_setup_requires_explicit_motor_enable_flag(monkeypatch, capsys):
    from agile_nero.robot.diagnostics import cli, commission

    setup = Mock()
    monkeypatch.setattr(commission, "enable_feedback", setup)
    monkeypatch.setattr(sys, "argv", ["nero", "enable-feedback", "--firmware", "1.11"])
    assert cli.main() == 1
    assert "requires explicit --enable-motors" in json.loads(capsys.readouterr().out)["error"]
    setup.assert_not_called()


def test_opt_in_cli_dispatches_to_canonical_setup_module(monkeypatch, capsys):
    from agile_nero.robot.diagnostics import cli, commission

    setup = Mock(return_value={"passed": True, "motion_target_frames_sent": 0})
    monkeypatch.setattr(commission, "enable_feedback", setup)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "nero",
            "enable-feedback",
            "--firmware",
            "1.11",
            "--enable-motors",
            "--serial",
            "test-adapter",
            "--seconds",
            "2",
        ],
    )
    assert cli.main() == 0
    assert json.loads(capsys.readouterr().out)["motion_target_frames_sent"] == 0
    setup.assert_called_once_with("test-adapter", 1000000, 2.0, "1.11")


def test_wrong_firmware_is_rejected_before_decoder_creation(monkeypatch):
    from agile_nero.robot.diagnostics import commission

    decoder = Mock()
    monkeypatch.setattr(commission, "StateDecoder", decoder)
    with pytest.raises(ValueError, match="firmware 1.11 only"):
        commission.enable_feedback("test", 1000000, 2, "1.12")
    decoder.assert_not_called()


def test_legacy_commission_import_keeps_module_identity():
    import agile_nero.commission as legacy
    from agile_nero.robot.diagnostics import commission

    assert legacy is commission


def bus_stub():
    bus = object.__new__(FeedbackSetupBus)
    bus._device = Mock()
    bus._is_shutdown = True
    bus.tx_firmware_queries = 0
    bus.tx_records = []
    return bus


def test_pinned_sdk_enable_sequence_matches_exact_allowlist():
    decoder = StateDecoder("v111")
    bus = bus_stub()
    decoder.robot._send_msg = lambda value: bus.send(decoder.robot._parser.pack(value))
    try:
        assert decoder.robot.enable() is False
        assert [x["purpose"] for x in bus.tx_records] == [
            "enable_all_motors",
            "normal_single_arm_mode",
            "enable_can_feedback",
        ]
        assert bus._device.send.call_count == 3
        with pytest.raises(can.CanOperationError):
            decoder.robot.move_j([0.0] * 7)
        assert bus._device.send.call_count == 3
    finally:
        decoder.close()
        bus._device = None


@pytest.mark.parametrize(
    "ident,data",
    [
        (0x154, b"\x00" * 8),
        (0x170, b"\x00" * 8),
        (0x180, b"\x00" * 8),
        (0x151, bytes.fromhex("0101320000000100")),
        (0x470, bytes.fromhex("fa00000000000000")),
        (0x471, bytes.fromhex("0801000000000000")),
    ],
)
def test_targets_mode_variants_and_disable_are_blocked(ident, data):
    bus = bus_stub()
    try:
        with pytest.raises(can.CanOperationError):
            bus.send(can.Message(arbitration_id=ident, data=data, is_extended_id=False))
        bus._device.send.assert_not_called()
    finally:
        bus._device = None


def test_only_reviewed_frames_are_in_allowlist():
    assert {ident for ident, _ in SETUP_FRAMES} == {0x471, 0x470, 0x151, 0x4AF}
