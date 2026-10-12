"""Native candleLight diagnostics: receive data and query firmware only.

gs-usb 0.3.1 resets USB and detaches a kernel driver on Darwin. Native
interface claiming works on this Mac without either operation. Starting
the adapter changes its USB acquisition mode; CAN ACKs are handled
by adapter hardware. All motor/mode/configuration CAN frames are rejected.
"""

import math
import time

import can
import usb.core
import usb.util
from gs_usb.constants import GS_CAN_MODE_HW_TIMESTAMP
from gs_usb.gs_usb import GsUsb
from gs_usb.gs_usb_frame import GS_USB_NONE_ECHO_ID, GsUsbFrame
from gs_usb.gs_usb_structures import DeviceMode
from usb.backend import libusb1

FIRMWARE_QUERY_ID = 0x4AF
FIRMWARE_QUERY_DATA = b"\x01"


def devices():
    if libusb1.get_backend() is None:
        raise RuntimeError("libusb is unavailable. On Apple Silicon: brew install libusb")
    return GsUsb.scan()


def select_device(channel):
    found = devices()
    if isinstance(channel, str) and channel not in ("", "auto"):
        matched = [d for d in found if d.serial_number == channel]
    elif isinstance(channel, int):
        matched = found[channel : channel + 1] if channel >= 0 else []
    else:
        matched = found if len(found) == 1 else []
    if len(matched) != 1:
        raise can.CanInitializationError(
            f"Expected one adapter for channel={channel!r}; found {len(found)}. "
            "Run nero devices and select its serial number."
        )
    return matched[0]


class NativeGsUsbBus(can.BusABC):
    """Local python-can backend; send() accepts only the firmware-info query."""

    def __init__(self, channel="auto", bitrate=1_000_000, **kwargs):
        self._device = None
        self._is_shutdown = True
        self.tx_firmware_queries = 0
        self.rx_counts = {}
        self.rx_error_frames = 0
        self.rx_last_seen = {}
        device = select_device(channel)
        self._device = device
        self.channel_info = f"candleLight serial={device.serial_number}"
        try:
            usb.util.claim_interface(device.gs_usb, 0)
            device.gs_usb.clear_halt(0x81)
            device.gs_usb.clear_halt(0x02)
            if not device.set_bitrate(bitrate):
                raise can.CanInitializationError(f"Unsupported bitrate {bitrate}")
            flags = GS_CAN_MODE_HW_TIMESTAMP & device.device_capability.feature
            device.device_flags = flags
            device.gs_usb.ctrl_transfer(0x41, 2, 0, 0, DeviceMode(1, flags).pack())
            super().__init__(channel=channel, **kwargs)
        except Exception:
            self.shutdown()
            raise

    def send(self, msg, timeout=None):
        if (
            msg.arbitration_id != FIRMWARE_QUERY_ID
            or bytes(msg.data) != FIRMWARE_QUERY_DATA
            or msg.dlc != 1
            or msg.is_extended_id
            or msg.is_remote_frame
            or msg.is_error_frame
        ):
            raise can.CanOperationError("Diagnostics backend blocks all non-firmware CAN writes")
        self._device.send(GsUsbFrame(can_id=FIRMWARE_QUERY_ID, data=list(msg.data)))
        self.tx_firmware_queries += 1

    def _recv_internal(self, timeout):
        frame = GsUsbFrame()
        has_timestamp = bool(self._device.device_flags & GS_CAN_MODE_HW_TIMESTAMP)
        timeout_ms = max(1, math.ceil((timeout if timeout is not None else 0.1) * 1000))
        try:
            raw = self._device.gs_usb.read(0x81, frame.__sizeof__(has_timestamp), timeout_ms)
        except usb.core.USBTimeoutError:
            return None, False
        except usb.core.USBError as exc:
            raise can.CanOperationError(f"USB receive failed: {exc}") from exc
        GsUsbFrame.unpack_into(frame, raw, has_timestamp)
        msg = can.Message(
            timestamp=frame.timestamp,
            arbitration_id=frame.arbitration_id,
            is_extended_id=frame.is_extended_id,
            is_remote_frame=frame.is_remote_frame,
            is_error_frame=frame.is_error_frame,
            dlc=frame.can_dlc,
            data=bytearray(frame.data)[: frame.can_dlc],
            channel=self.channel_info,
            is_rx=frame.echo_id == GS_USB_NONE_ECHO_ID,
        )
        if msg.is_error_frame:
            self.rx_error_frames += 1
        elif msg.is_rx:
            key = f"0x{msg.arbitration_id:03X}"
            self.rx_counts[key] = self.rx_counts.get(key, 0) + 1
            self.rx_last_seen[key] = time.monotonic()
        return msg, False

    def shutdown(self):
        if self._device is not None:
            # Match SocketCAN socket-close semantics: leave adapter CAN active
            # so its hardware still ACKs. Earlier close/reopen tests coincided
            # with lost feedback; keep ACK active to remove that possible cause.
            usb.util.dispose_resources(self._device.gs_usb)
            self._device = None
        super().shutdown()
