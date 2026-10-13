"""Robot tests are strictly offline: real transport access is a test failure."""

import socket

import can
import pytest
import usb.core


@pytest.fixture(autouse=True)
def block_real_device_io(monkeypatch):
    def blocked(*args, **kwargs):
        raise AssertionError("Robot tests must use simulated I/O, never real devices")

    monkeypatch.setattr(usb.core, "find", blocked)
    for name in ("read", "write", "ctrl_transfer", "reset", "clear_halt"):
        monkeypatch.setattr(usb.core.Device, name, blocked)
    for name in ("connect", "connect_ex", "bind", "send", "sendto", "sendall"):
        monkeypatch.setattr(socket.socket, name, blocked)
    monkeypatch.setattr(can, "Bus", blocked)
    monkeypatch.setattr(can.interface, "Bus", blocked)
