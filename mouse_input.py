"""Windows WM_INPUT adapter. Never uses the screen pointer for displacement.

RIDEV_INPUTSINK keeps motion flowing at screen edges / in the background.
Legacy mouse messages remain enabled. Returning False lets Qt/DefWindowProc
perform foreground WM_INPUT cleanup. All Win32 pointer signatures are explicit.
"""

import ctypes as C
import os
import time

from PySide6.QtCore import QAbstractNativeEventFilter, QObject, Signal

from input_handler import RawPacket

U16, U32, I32 = C.c_uint16, C.c_uint32, C.c_int32
HANDLE = C.c_void_p


class BUTTONS(C.Structure):
    _fields_ = [("flags", U16), ("data", U16)]


class BUTTONUNION(C.Union):
    _fields_ = [("value", U32), ("parts", BUTTONS)]


class RAWMOUSE(C.Structure):
    _fields_ = [
        ("flags", U16),
        ("buttons", BUTTONUNION),
        ("raw_buttons", U32),
        ("dx", I32),
        ("dy", I32),
        ("extra", U32),
    ]


class RAWINPUTHEADER(C.Structure):
    _fields_ = [
        ("type", U32),
        ("size", U32),
        ("device", HANDLE),
        ("wparam", C.c_size_t),
    ]


class RAWINPUTDEVICE(C.Structure):
    _fields_ = [("page", U16), ("usage", U16), ("flags", U32), ("target", HANDLE)]


class DEVICELIST(C.Structure):
    _fields_ = [("device", HANDLE), ("type", U32)]


class POINT(C.Structure):
    _fields_ = [("x", I32), ("y", I32)]


class MSG(C.Structure):
    _fields_ = [
        ("hwnd", HANDLE),
        ("message", U32),
        ("wparam", C.c_size_t),
        ("lparam", C.c_ssize_t),
        ("time", U32),
        ("point", POINT),
        ("private", U32),
    ]


def decode_mouse(data: bytes, device: str, timestamp: float) -> RawPacket | None:
    if len(data) < C.sizeof(RAWINPUTHEADER):
        raise ValueError("Truncated Raw Input header")
    header = RAWINPUTHEADER.from_buffer_copy(data)
    if header.type != 0:
        return None
    needed = C.sizeof(RAWINPUTHEADER) + C.sizeof(RAWMOUSE)
    if len(data) < needed or header.size < needed or header.size > len(data):
        raise ValueError("Truncated or invalid Raw Input mouse packet")
    mouse = RAWMOUSE.from_buffer_copy(data, C.sizeof(RAWINPUTHEADER))
    return RawPacket(
        device,
        mouse.dx,
        mouse.dy,
        mouse.buttons.parts.flags,
        timestamp,
        bool(mouse.flags & 1),
        bool(mouse.flags & 4),
    )


class RawInput(QAbstractNativeEventFilter, QObject):
    packet = Signal(object)
    error = Signal(str)
    removed = Signal(str)

    def __init__(self):
        QAbstractNativeEventFilter.__init__(self)
        QObject.__init__(self)
        self.registered = False
        self.devices = {}
        if os.name != "nt":
            raise RuntimeError("Physical mouse tracking requires Windows 11.")
        self.user32 = C.WinDLL("user32", use_last_error=True)
        u = self.user32
        u.RegisterRawInputDevices.argtypes = [C.POINTER(RAWINPUTDEVICE), U32, U32]
        u.RegisterRawInputDevices.restype = C.c_int
        u.GetRawInputData.argtypes = [HANDLE, U32, HANDLE, C.POINTER(U32), U32]
        u.GetRawInputData.restype = U32
        u.GetRawInputDeviceInfoW.argtypes = [HANDLE, U32, HANDLE, C.POINTER(U32)]
        u.GetRawInputDeviceInfoW.restype = U32
        u.GetRawInputDeviceList.argtypes = [C.POINTER(DEVICELIST), C.POINTER(U32), U32]
        u.GetRawInputDeviceList.restype = U32
        u.GetDoubleClickTime.restype = U32
        u.GetMessageTime.restype = I32
        u.GetForegroundWindow.restype = HANDLE
        self.kernel32 = C.WinDLL("kernel32", use_last_error=True)
        self.kernel32.GetTickCount64.restype = C.c_uint64

    @property
    def double_click_interval(self):
        return self.user32.GetDoubleClickTime() / 1000.0

    def start(self, hwnd, application):
        device = RAWINPUTDEVICE(1, 2, 0x100 | 0x2000, hwnd)
        if not self.user32.RegisterRawInputDevices(
            C.byref(device), 1, C.sizeof(device)
        ):
            raise C.WinError(C.get_last_error())
        application.installNativeEventFilter(self)
        self.application = application
        self.hwnd = hwnd
        self.registered = True

    def stop(self):
        if self.registered:
            self.application.removeNativeEventFilter(self)
            device = RAWINPUTDEVICE(1, 2, 1, None)  # RIDEV_REMOVE
            if not self.user32.RegisterRawInputDevices(
                C.byref(device), 1, C.sizeof(device)
            ):
                self.error.emit(f"Unable to unregister raw input: {C.get_last_error()}")
            self.registered = False

    def device_name(self, handle):
        if handle in self.devices:
            return self.devices[handle]
        size = U32()
        result = self.user32.GetRawInputDeviceInfoW(
            handle, 0x20000007, None, C.byref(size)
        )
        if result == 0xFFFFFFFF or not size.value:
            raise RuntimeError(
                "Mouse identity unavailable. Remote / injected input is unsupported."
            )
        buffer = C.create_unicode_buffer(size.value + 1)
        if (
            self.user32.GetRawInputDeviceInfoW(
                handle, 0x20000007, buffer, C.byref(size)
            )
            == 0xFFFFFFFF
        ):
            raise C.WinError(C.get_last_error())
        self.devices[handle] = buffer.value
        return buffer.value

    def enumerate_mice(self):
        count = U32()
        if (
            self.user32.GetRawInputDeviceList(
                None, C.byref(count), C.sizeof(DEVICELIST)
            )
            == 0xFFFFFFFF
        ):
            raise C.WinError(C.get_last_error())
        items = (DEVICELIST * count.value)()
        result = self.user32.GetRawInputDeviceList(
            items, C.byref(count), C.sizeof(DEVICELIST)
        )
        if result == 0xFFFFFFFF:
            raise C.WinError(C.get_last_error())
        return [
            self.device_name(v.device)
            for v in items[:result]
            if v.type == 0 and v.device
        ]

    def nativeEventFilter(self, event_type, message):
        try:
            msg = MSG.from_address(int(message))
            if (
                msg.message == 0xFE and msg.wparam == 2
            ):  # WM_INPUT_DEVICE_CHANGE removal
                device = self.devices.pop(msg.lparam, "")
                if device:
                    self.removed.emit(device)
            elif msg.message == 0xFF:
                size = U32()
                r = self.user32.GetRawInputData(
                    msg.lparam,
                    0x10000003,
                    None,
                    C.byref(size),
                    C.sizeof(RAWINPUTHEADER),
                )
                if (
                    r == 0xFFFFFFFF
                    or size.value > 4096
                    or size.value < C.sizeof(RAWINPUTHEADER)
                ):
                    raise RuntimeError("Unable to read Raw Input packet size")
                buf = C.create_string_buffer(size.value)
                read = self.user32.GetRawInputData(
                    msg.lparam, 0x10000003, buf, C.byref(size), C.sizeof(RAWINPUTHEADER)
                )
                if read == 0xFFFFFFFF or read != size.value:
                    raise RuntimeError("Raw Input packet was lost or truncated")
                header = RAWINPUTHEADER.from_buffer_copy(buf)
                if header.type == 0:
                    if not header.device:
                        # SendInput and some remote sessions have no physical device identity.
                        return False, 0
                    name = self.device_name(header.device)
                    age_ms = (
                        (self.kernel32.GetTickCount64() & 0xFFFFFFFF) - msg.time
                    ) & 0xFFFFFFFF
                    timestamp = time.monotonic() - age_ms / 1000.0
                    packet = decode_mouse(buf.raw, name, timestamp)
                    self.packet.emit(packet)
        except Exception as exc:
            # Native callbacks cannot propagate exceptions through Windows.
            self.error.emit(f"Raw Input: {exc}")
        return False, 0
