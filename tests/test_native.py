import ctypes as C
import os

import pytest

from mouse_input import (
    MSG,
    RAWINPUTDEVICE,
    RAWINPUTHEADER,
    RAWMOUSE,
    decode_mouse,
)


def packet_bytes(dx=-100, dy=250, flags=0, buttons=1):
    h = RAWINPUTHEADER(0, C.sizeof(RAWINPUTHEADER) + C.sizeof(RAWMOUSE), 123, 0)
    m = RAWMOUSE()
    m.dx = dx
    m.dy = dy
    m.flags = flags
    m.buttons.parts.flags = buttons
    return bytes(h) + bytes(m)


def test_win32_layout():
    assert C.sizeof(RAWMOUSE) == 24
    assert RAWMOUSE.dx.offset == 12
    assert RAWMOUSE.dy.offset == 16
    assert RAWMOUSE.buttons.offset == 4
    assert C.sizeof(RAWINPUTHEADER) == (24 if C.sizeof(C.c_void_p) == 8 else 16)
    assert C.sizeof(RAWINPUTDEVICE) == (16 if C.sizeof(C.c_void_p) == 8 else 12)
    assert C.sizeof(MSG) == (48 if C.sizeof(C.c_void_p) == 8 else 32)


def test_decode_signed_movement():
    p = decode_mouse(packet_bytes(), "mouse", 1.5)
    assert (p.dx, p.dy, p.buttons, p.timestamp) == (-100, 250, 1, 1.5)
    assert not p.absolute


def test_decode_absolute():
    assert decode_mouse(packet_bytes(flags=1), "mouse", 0).absolute


@pytest.mark.parametrize("data", [b"", b"0" * 12, packet_bytes()[:-1]])
def test_truncated_rejected(data):
    with pytest.raises(ValueError):
        decode_mouse(data, "mouse", 0)


@pytest.mark.skipif(os.name != "nt", reason="Windows API")
def test_real_windows_registration_and_enumeration():
    # A separate native process is required: the main GUI test process is offscreen.
    import subprocess
    import sys
    from pathlib import Path

    env = dict(os.environ, QT_QPA_PLATFORM="windows")
    script = """
from PySide6.QtWidgets import QApplication, QWidget
from mouse_input import RawInput
app=QApplication([])
w=QWidget()
raw=RawInput()
raw.start(int(w.winId()),app)
assert raw.registered
mice=raw.enumerate_mice()
assert isinstance(mice,list)
assert all(isinstance(v,str) and v for v in mice)
assert 0.01 <= raw.double_click_interval <= 5
app.processEvents()
raw.stop()
assert not raw.registered
w.close()
print("native-registration-ok",len(mice))
"""
    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=Path(__file__).resolve().parents[1],
        env=env,
        capture_output=True,
        text=True,
        timeout=20,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "native-registration-ok" in result.stdout
