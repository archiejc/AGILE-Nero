"""Verify diagnostics cannot transmit motor or mode commands; no hardware used."""

from unittest.mock import Mock

import can
import pytest

from agile_nero.robot.diagnostics.transport import NativeGsUsbBus, select_device


def test_legacy_diagnostic_modules_preserve_patch_targets():
    import agile_nero.cli as old_cli
    import agile_nero.state as old_state
    import agile_nero.transport as old_transport
    from agile_nero.robot.diagnostics import cli, state, transport

    assert old_cli is cli
    assert old_state is state
    assert old_transport is transport


def test_firmware_query_is_the_only_write_allowed():
    bus = object.__new__(NativeGsUsbBus)
    bus._device = Mock()
    bus._is_shutdown = True
    bus.tx_firmware_queries = 0
    bus.send(can.Message(arbitration_id=0x4AF, data=[1], is_extended_id=False))
    assert bus.tx_firmware_queries == 1
    assert bus._device.send.call_count == 1
    frame = bus._device.send.call_args.args[0]
    assert frame.can_id == 0x4AF and frame.can_dlc == 1
    bus._device = None


@pytest.mark.parametrize(
    "message",
    [
        can.Message(arbitration_id=0x151, data=[1] * 8, is_extended_id=False),
        can.Message(arbitration_id=0x150, data=[1] * 8, is_extended_id=False),
        can.Message(arbitration_id=0x4AF, data=[2], is_extended_id=False),
        can.Message(arbitration_id=0x4AF, data=[1, 0], is_extended_id=False),
        can.Message(arbitration_id=0x4AF, data=[1], is_extended_id=True),
        can.Message(arbitration_id=0x4AF, is_remote_frame=True, is_extended_id=False),
        can.Message(arbitration_id=0x4AF, data=[1], is_error_frame=True, is_extended_id=False),
    ],
)
def test_control_and_malformed_frames_are_blocked(message):
    bus = object.__new__(NativeGsUsbBus)
    bus._device = Mock()
    bus._is_shutdown = True
    bus.tx_firmware_queries = 0
    with pytest.raises(can.CanOperationError):
        bus.send(message)
    bus._device.send.assert_not_called()
    assert bus.tx_firmware_queries == 0
    bus._device = None


def test_multiple_adapters_require_explicit_selection(monkeypatch):
    adapters = [Mock(serial_number="first"), Mock(serial_number="second")]
    monkeypatch.setattr("agile_nero.robot.diagnostics.transport.devices", lambda: adapters)
    with pytest.raises(can.CanInitializationError):
        select_device("auto")
    assert select_device("second") is adapters[1]


def test_backend_is_available_to_sdk_without_dynamic_patching():
    from can.util import load_config

    config = load_config(config={"interface": "nero_gs_usb", "channel": "auto"})
    assert config["interface"] == "nero_gs_usb"


def test_open_and_close_preserve_can_ack_peer(monkeypatch):
    device = Mock(serial_number="test")
    device.device_capability.feature = 0x10
    device.set_bitrate.return_value = True
    claim = Mock()
    dispose = Mock()
    monkeypatch.setattr("agile_nero.robot.diagnostics.transport.select_device", lambda _: device)
    monkeypatch.setattr("agile_nero.robot.diagnostics.transport.usb.util.claim_interface", claim)
    monkeypatch.setattr(
        "agile_nero.robot.diagnostics.transport.usb.util.dispose_resources", dispose
    )
    bus = NativeGsUsbBus(channel="test")
    claim.assert_called_once_with(device.gs_usb, 0)
    assert device.gs_usb.clear_halt.call_args_list[0].args == (0x81,)
    assert device.gs_usb.clear_halt.call_args_list[1].args == (0x02,)
    bus.shutdown()
    bus.shutdown()
    device.stop.assert_not_called()
    dispose.assert_called_once_with(device.gs_usb)
