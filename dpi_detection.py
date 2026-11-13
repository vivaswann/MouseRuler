"""Read-only HID resolution probe. Never confuses screen DPI / polling rate with CPI.

Most mouse descriptors omit physical units, so a manual hardware-DPI value is
normally required. A descriptor-derived value is only a reported resolution,
not proof that a vendor's currently selected DPI stage matches it.
"""

import ctypes as C
import os
from dataclasses import dataclass
from math import isfinite

U8, U16, U32, I32 = C.c_ubyte, C.c_uint16, C.c_uint32, C.c_int32


class HIDP_CAPS(C.Structure):
    _fields_ = [
        ("Usage", U16),
        ("UsagePage", U16),
        ("InputReportByteLength", U16),
        ("OutputReportByteLength", U16),
        ("FeatureReportByteLength", U16),
        ("Reserved", U16 * 17),
    ] + [
        (n, U16)
        for n in (
            "NumberLinkCollectionNodes",
            "NumberInputButtonCaps",
            "NumberInputValueCaps",
            "NumberInputDataIndices",
            "NumberOutputButtonCaps",
            "NumberOutputValueCaps",
            "NumberOutputDataIndices",
            "NumberFeatureButtonCaps",
            "NumberFeatureValueCaps",
            "NumberFeatureDataIndices",
        )
    ]


class HIDP_VALUE_CAPS(C.Structure):
    _fields_ = [
        ("UsagePage", U16),
        ("ReportID", U8),
        ("IsAlias", U8),
        ("BitField", U16),
        ("LinkCollection", U16),
        ("LinkUsage", U16),
        ("LinkUsagePage", U16),
        ("IsRange", U8),
        ("IsStringRange", U8),
        ("IsDesignatorRange", U8),
        ("IsAbsolute", U8),
        ("HasNull", U8),
        ("Reserved", U8),
        ("BitSize", U16),
        ("ReportCount", U16),
        ("Reserved2", U16 * 5),
        ("UnitsExp", U32),
        ("Units", U32),
        ("LogicalMin", I32),
        ("LogicalMax", I32),
        ("PhysicalMin", I32),
        ("PhysicalMax", I32),
        ("UsageData", U16 * 8),
    ]


@dataclass(frozen=True)
class DpiDetection:
    dpi: float | None
    explanation: str
    source: str = "HID physical resolution"


def dpi_scale(dpi):
    if (
        not isinstance(dpi, (int, float))
        or isinstance(dpi, bool)
        or not isfinite(dpi)
        or not 1 <= dpi <= 1_000_000
    ):
        raise ValueError("Enter a hardware DPI between 1 and 1,000,000.")
    return 25.4 / dpi


def resolution_from_caps(caps):
    axes = {0x30: [], 0x31: []}
    for cap in caps:
        if cap.UsagePage != 1 or cap.IsAbsolute or cap.IsAlias:
            continue
        # HID linear SI centimetres (0x11), or linear English inches (0x13).
        # Reject compound units (acceleration, velocity, angle, etc.).
        if cap.Units not in (0x11, 0x13):
            continue
        logical = cap.LogicalMax - cap.LogicalMin
        physical = cap.PhysicalMax - cap.PhysicalMin
        if logical <= 0 or physical <= 0:
            continue
        exp = cap.UnitsExp & 0xF
        exp = exp - 16 if exp >= 8 else exp
        physical_mm = physical * (10.0 if cap.Units == 0x11 else 25.4) * 10**exp
        dpi = logical * 25.4 / physical_mm
        try:
            dpi_scale(dpi)
        except ValueError:
            continue
        lo = cap.UsageData[0]
        hi = cap.UsageData[1] if cap.IsRange else lo
        for axis in axes:
            if lo <= axis <= hi:
                axes[axis].append(dpi)
    if any(len(values) != 1 for values in axes.values()):
        return DpiDetection(
            None,
            "This mouse does not expose an unambiguous physical X/Y resolution. Enter its hardware DPI.",
        )
    x, y = axes[0x30][0], axes[0x31][0]
    if abs(x - y) > max(x, y) * 0.001:
        return DpiDetection(
            None,
            "The mouse reports different X/Y resolutions. Use ruler calibration instead of one DPI value.",
        )
    return DpiDetection(
        (x + y) / 2,
        "HID-reported resolution found. Confirm it matches the current DPI setting in your mouse software.",
    )


def detect_mouse_dpi(device_path, raw_handle=None):
    if os.name != "nt" or not device_path or not device_path.startswith("\\\\?\\"):
        return DpiDetection(
            None,
            "Hardware DPI cannot be read for this device. Enter the DPI selected in your mouse software.",
        )
    kernel = C.WinDLL("kernel32", use_last_error=True)
    hid = C.WinDLL("hid", use_last_error=True)
    kernel.CreateFileW.argtypes = [
        C.c_wchar_p,
        U32,
        U32,
        C.c_void_p,
        U32,
        U32,
        C.c_void_p,
    ]
    kernel.CreateFileW.restype = C.c_void_p
    kernel.CloseHandle.argtypes = [C.c_void_p]
    kernel.CloseHandle.restype = C.c_int
    hid.HidD_GetPreparsedData.argtypes = [C.c_void_p, C.POINTER(C.c_void_p)]
    hid.HidD_GetPreparsedData.restype = U8
    hid.HidD_FreePreparsedData.argtypes = [C.c_void_p]
    hid.HidD_FreePreparsedData.restype = U8
    hid.HidP_GetCaps.argtypes = [C.c_void_p, C.POINTER(HIDP_CAPS)]
    hid.HidP_GetCaps.restype = I32
    hid.HidP_GetValueCaps.argtypes = [
        C.c_int,
        C.POINTER(HIDP_VALUE_CAPS),
        C.POINTER(U16),
        C.c_void_p,
    ]
    hid.HidP_GetValueCaps.restype = I32

    def read_preparsed(preparsed):
        caps = HIDP_CAPS()
        if (
            hid.HidP_GetCaps(preparsed, C.byref(caps)) != 0x110000
            or not caps.NumberInputValueCaps
        ):
            return DpiDetection(
                None,
                "No physical resolution information is available. Enter its hardware DPI.",
            )
        count = U16(caps.NumberInputValueCaps)
        values = (HIDP_VALUE_CAPS * count.value)()
        if hid.HidP_GetValueCaps(0, values, C.byref(count), preparsed) != 0x110000:
            return DpiDetection(
                None, "HID resolution could not be read. Enter its hardware DPI."
            )
        return resolution_from_caps(values[: count.value])

    if raw_handle:
        user = C.WinDLL("user32", use_last_error=True)
        user.GetRawInputDeviceInfoW.argtypes = [
            C.c_void_p,
            U32,
            C.c_void_p,
            C.POINTER(U32),
        ]
        user.GetRawInputDeviceInfoW.restype = U32
        size = U32()
        # Raw Input's metadata path can work even when opening the protected
        # mouse HID collection directly is not permitted.
        result = user.GetRawInputDeviceInfoW(
            raw_handle, 0x20000005, None, C.byref(size)
        )
        if result != 0xFFFFFFFF and 0 < size.value <= 1_000_000:
            data = C.create_string_buffer(size.value)
            if (
                user.GetRawInputDeviceInfoW(raw_handle, 0x20000005, data, C.byref(size))
                != 0xFFFFFFFF
            ):
                return read_preparsed(C.cast(data, C.c_void_p))
    # No read/write access, no feature/output reports and no mouse setting changes.
    handle = kernel.CreateFileW(device_path, 0, 3, None, 3, 0, None)
    if handle in (None, C.c_void_p(-1).value):
        return DpiDetection(
            None,
            "Windows does not allow reading resolution metadata for this mouse. Enter its hardware DPI.",
        )
    preparsed = C.c_void_p()
    try:
        if not hid.HidD_GetPreparsedData(handle, C.byref(preparsed)):
            return DpiDetection(
                None,
                "This device does not expose readable HID resolution metadata. Enter its hardware DPI.",
            )
        return read_preparsed(preparsed)
    finally:
        if preparsed:
            hid.HidD_FreePreparsedData(preparsed)
        kernel.CloseHandle(handle)
