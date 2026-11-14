"""Read-only HID product identification; receivers do not identify their mice."""

import ctypes as C
import os
import re
from dataclasses import dataclass
from urllib.parse import urlencode


@dataclass(frozen=True)
class MouseIdentity:
    name: str
    model_known: bool = False
    vendor_id: str = ""
    product_id: str = ""


VENDORS = {
    "046D": "Logitech",
    "1532": "Razer",
    "045E": "Microsoft",
    "1B1C": "Corsair",
    "1038": "SteelSeries",
}


def identity_from_strings(path, product="", manufacturer=""):
    vid = re.search(r"VID_([0-9A-F]{4})", path, re.I)
    pid = re.search(r"PID_([0-9A-F]{4})", path, re.I)
    vid = vid.group(1).upper() if vid else ""
    pid = pid.group(1).upper() if pid else ""
    product = " ".join(product.split())[:100]
    brand = VENDORS.get(vid, " ".join(manufacturer.split())[:60])
    generic = (
        "receiver",
        "dongle",
        "hid-compliant",
        "usb optical mouse",
        "usb gaming mouse",
        "2.4g",
        "wireless device",
    )
    known = bool(
        product
        and product.casefold() not in ("mouse", "usb mouse", "gaming mouse")
        and not any(x in product.casefold() for x in generic)
    )
    name = (
        product if known else f"{brand + ' ' if brand else ''}mouse · model unavailable"
    )
    return MouseIdentity(name, known, vid, pid)


def identify_mouse(path):
    fallback = identity_from_strings(path)
    if os.name != "nt" or not path.startswith("\\\\?\\"):
        return fallback
    kernel = C.WinDLL("kernel32", use_last_error=True)
    hid = C.WinDLL("hid", use_last_error=True)
    kernel.CreateFileW.argtypes = [
        C.c_wchar_p,
        C.c_uint32,
        C.c_uint32,
        C.c_void_p,
        C.c_uint32,
        C.c_uint32,
        C.c_void_p,
    ]
    kernel.CreateFileW.restype = C.c_void_p
    kernel.CloseHandle.argtypes = [C.c_void_p]
    kernel.CloseHandle.restype = C.c_int
    handle = kernel.CreateFileW(path, 0, 3, None, 3, 0, None)
    if handle in (None, C.c_void_p(-1).value):
        return fallback
    try:
        values = []
        for name in ("HidD_GetProductString", "HidD_GetManufacturerString"):
            func = getattr(hid, name)
            func.argtypes = [C.c_void_p, C.c_void_p, C.c_uint32]
            func.restype = C.c_ubyte
            text = C.create_unicode_buffer(128)
            values.append(text.value if func(handle, text, C.sizeof(text)) else "")
        return identity_from_strings(path, *values)
    finally:
        kernel.CloseHandle(handle)


def wheel_search_url(identity):
    # Never transmit device instance paths, serial numbers, or device hashes.
    name = identity.name.split(" · ")[0]
    return "https://www.google.com/search?" + urlencode(
        {
            "q": f"{name} scroll wheel outer diameter mm increments per revolution specifications"
        }
    )


MODEL_HINTS = (
    {
        "name": "Razer DeathAdder V4 Pro",
        "steps": 24,
        "source": "https://mysupport.razer.com/app/answers/detail/a_id/19852",
        "note": "Manufacturer lists 24 wheel steps. Outer wheel diameter is not published here; confirm reported steps with the one-turn helper.",
    },
    {
        "name": "Razer Viper V4 Pro",
        "steps": 24,
        "source": "https://mysupport.razer.com/app/answers/detail/a_id/20775",
        "note": "Manufacturer lists 24 wheel steps. Outer wheel diameter is not published here; confirm reported steps with the one-turn helper.",
    },
    {
        "name": "Razer Naga V3 Pro",
        "steps": None,
        "source": "https://mysupport.razer.com/app/answers/detail/a_id/21025",
        "note": "24-step and 48-step modes are selectable. Turn off free-spin / Smart-Reel and count your current mode; diameter remains unknown.",
    },
    {
        "name": "Razer Naga V2 Pro",
        "steps": None,
        "source": "https://www.razer.com/technology/razer-scroll-wheels",
        "note": "Wheel step count is configurable from 8 to 96. Count the current mode; diameter remains unknown.",
    },
    {
        "name": "Razer Basilisk V4 Pro",
        "steps": None,
        "source": "https://mysupport.razer.com/app/answers/detail/a_id/21064",
        "note": "24-step and 48-step modes are selectable. Disable free-spin / Smart-Reel before measuring; diameter remains unknown.",
    },
)


def model_hint(identity):
    if not identity.model_known:
        return None
    return next(
        (m for m in MODEL_HINTS if identity.name.casefold() == m["name"].casefold()),
        None,
    )
