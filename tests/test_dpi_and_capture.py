import ctypes as C
import os
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from cursor_capture import RECT, CursorCapture
from dpi_detection import (
    HIDP_CAPS,
    HIDP_VALUE_CAPS,
    DpiDetection,
    detect_mouse_dpi,
    dpi_scale,
    resolution_from_caps,
)
from input_handler import RawPacket as P
from measurement_state import Measurement, State
from settings import Settings


@pytest.mark.parametrize("dpi", [400, 800, 1600, 3200, 25600])
def test_dpi_conversion(dpi):
    m = Measurement()
    m.start("mouse", dpi_scale(dpi), "dpi")
    m.feed(dpi, 0, "mouse")
    assert m.trajectory.distances.direct == pytest.approx(25.4)
    assert m.physical_units and not m.calibrated
    assert m.scale_source == "dpi"


def test_fast_finish_pair_after_real_motion(window):
    window.save_dpi("test-mouse", 800)
    for t, b in [(1, 1), (1.01, 2), (1.1, 1), (1.11, 2)]:
        window.router.feed(P("test-mouse", buttons=b, timestamp=t))
    window.router.feed(P("test-mouse", 100, 0, timestamp=1.15))
    for t, b in [(1.2, 1), (1.21, 2), (1.3, 1), (1.31, 2)]:
        window.router.feed(P("test-mouse", buttons=b, timestamp=t))
    assert window.measurement.state == State.COMPLETED
    assert window.measurement.trajectory.distances.direct == pytest.approx(3.175)


@pytest.mark.parametrize(
    "value", [0, -800, float("nan"), float("inf"), True, "800", None, 1_000_001]
)
def test_invalid_dpi(value):
    with pytest.raises(ValueError):
        dpi_scale(value)


def axis(usage, dpi=1600, units=0x13, exponent=0):
    cap = HIDP_VALUE_CAPS()
    cap.UsagePage = 1
    cap.UsageData[0] = usage
    cap.Units = units
    cap.UnitsExp = exponent
    cap.LogicalMin = 0
    cap.LogicalMax = dpi
    cap.PhysicalMin = 0
    cap.PhysicalMax = 1
    return cap


def test_hid_resolution_from_inches_and_layout():
    assert C.sizeof(HIDP_CAPS) == 64
    assert C.sizeof(HIDP_VALUE_CAPS) == 72
    assert HIDP_VALUE_CAPS.Units.offset == 36
    assert resolution_from_caps([axis(0x30), axis(0x31)]).dpi == 1600


def test_hid_centimetre_exponent():
    caps = [axis(v, 1000, 0x11, 0xF) for v in (0x30, 0x31)]  # 1000 counts per 0.1 cm
    assert resolution_from_caps(caps).dpi == pytest.approx(25400)


@pytest.mark.parametrize(
    "case", ["no_units", "absolute", "ambiguous", "anisotropic", "empty"]
)
def test_hid_never_invents_resolution(case):
    caps = [axis(0x30), axis(0x31)]
    if case == "no_units":
        caps[0].Units = 0
    elif case == "absolute":
        caps[0].IsAbsolute = True
    elif case == "ambiguous":
        caps.append(axis(0x30))
    elif case == "anisotropic":
        caps[0].LogicalMax = 800
    else:
        caps = []
    assert resolution_from_caps(caps).dpi is None


def test_unsupported_device_asks_for_dpi():
    result = detect_mouse_dpi("synthetic-device")
    assert result.dpi is None
    assert "Enter" in result.explanation


def test_dpi_lengths_in_all_units_without_ruler(window):
    window.save_dpi("test-mouse", 1600)
    window.command_button()
    window.router.feed(P("test-mouse", 960, 1280), False)
    window.command_button()
    window.refresh()
    assert window.measurement.trajectory.distances.direct == pytest.approx(25.4)
    assert window.result_unit.text() == "cm"
    expected = {"mm": "25.4000", "cm": "2.5400", "m": "0.0254", "in": "1.0000"}
    assert {
        u: widgets[0].text() for u, widgets in window.all_unit_values.items()
    } == expected
    assert "DPI-based estimate" in window.accuracy_label.text()
    assert "sensor counts only" not in window.accuracy_label.text()
    assert Settings(window.settings.path).dpi_profiles["test-mouse"]["dpi"] == 1600


def test_calibration_overrides_dpi_then_dpi_change_invalidates(window):
    window.save_dpi("test-mouse", 800)
    window.navigate(1)
    window.command_button()
    window.router.feed(P("test-mouse", 1000, 0), False)
    window.command_button()
    window.add_trial()
    window.save_calibration()
    window.command_button()
    assert window.measurement.scale == 0.1
    assert window.measurement.scale_source == "calibration"
    window.command_button()
    window.save_dpi("test-mouse", 1600)
    assert not window.settings.profiles
    assert not window.calibration.coefficients
    window.command_button()
    assert window.measurement.scale == dpi_scale(1600)


def test_dpi_save_rollback(window, monkeypatch):
    def fail():
        raise OSError("read-only")

    monkeypatch.setattr(window.settings, "save", fail)
    window.save_dpi("test-mouse", 800)
    assert not window.settings.dpi_profiles
    assert "could not be saved" in window.message.text()


def test_missing_dpi_opens_prompt_without_recording(window, monkeypatch):
    monkeypatch.setattr(window, "isVisible", lambda: False)
    window._requires_raw = True
    window.native = SimpleNamespace(registered=True, stop=lambda: None)
    calls = []
    monkeypatch.setattr(window, "configure_dpi", lambda **kw: calls.append(kw))
    window.command("test-mouse")
    assert calls == [{"device": "test-mouse"}]
    assert window.measurement.state == State.IDLE


def test_prompt_detected_value_and_confirmed_source(window, monkeypatch):
    import main

    monkeypatch.setattr(
        main, "detect_mouse_dpi", lambda _, **kw: DpiDetection(1600, "HID reported")
    )
    observed = []

    def enter(parent, title, text, value, *args):
        observed.append(value)
        return value, True

    monkeypatch.setattr(main.QInputDialog, "getDouble", enter)
    window.configure_dpi()
    assert observed == [1600]
    assert (
        window.settings.dpi_profiles["test-mouse"]["source"]
        == "HID reported (confirmed)"
    )
    assert window.measurement.state == State.IDLE


class FakeUser32:
    def __init__(self):
        self.rect = (0, 0, 1920, 1080)
        self.counter = 0
        self.clips = []

    def GetClipCursor(self, ptr):
        r = C.cast(ptr, C.POINTER(RECT)).contents
        r.left, r.top, r.right, r.bottom = self.rect
        return True

    def ClipCursor(self, ptr):
        self.rect = (
            CursorCapture.values(C.cast(ptr, C.POINTER(RECT)).contents)
            if ptr
            else (0, 0, 1920, 1080)
        )
        self.clips.append(self.rect)
        return True

    def ShowCursor(self, show):
        self.counter += 1 if show else -1
        return self.counter


def test_capture_hides_confines_and_balances_release(app, monkeypatch):
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QApplication

    api = FakeUser32()
    capture = CursorCapture(api)
    monkeypatch.setattr(capture, "rectangle", lambda _: RECT(100, 200, 700, 600))
    try:
        capture.acquire(object())
        assert capture.active and api.rect == (100, 200, 700, 600)
        assert api.counter < 0
        assert QApplication.overrideCursor().shape() == Qt.CursorShape.BlankCursor
        capture.release()
        capture.release()
        assert not capture.active and api.counter == 0
        assert api.rect == (0, 0, 1920, 1080)
        assert QApplication.overrideCursor() is None
    finally:
        capture.release()


def test_capture_tracks_new_graph_rectangle(app, monkeypatch):
    api = FakeUser32()
    capture = CursorCapture(api)
    monkeypatch.setattr(capture, "rectangle", lambda _: RECT(0, 0, 200, 200))
    try:
        capture.acquire(object())
        monkeypatch.setattr(capture, "rectangle", lambda _: RECT(300, 0, 500, 200))
        capture.update()
        assert api.rect == (300, 0, 500, 200)
    finally:
        capture.release()


def test_capture_does_not_overwrite_other_apps_clip(app, monkeypatch):
    api = FakeUser32()
    capture = CursorCapture(api)
    monkeypatch.setattr(capture, "rectangle", lambda _: RECT(100, 100, 200, 200))
    capture.acquire(object())
    api.rect = (800, 100, 1000, 500)
    capture.release()
    assert api.rect == (800, 100, 1000, 500) and api.counter == 0


def test_offscreen_graph_intersection_still_releases(app, monkeypatch):
    class CroppingAPI(FakeUser32):
        def ClipCursor(self, ptr):
            super().ClipCursor(ptr)
            self.rect = (
                max(0, self.rect[0]),
                max(0, self.rect[1]),
                min(1920, self.rect[2]),
                min(1080, self.rect[3]),
            )
            return True

    api = CroppingAPI()
    capture = CursorCapture(api)
    monkeypatch.setattr(capture, "rectangle", lambda _: RECT(-100, 100, 300, 400))
    try:
        capture.acquire(object())
        assert api.rect == (0, 100, 300, 400)
        capture.release()
        assert api.rect == (0, 0, 1920, 1080) and api.counter == 0
    finally:
        capture.release()


@pytest.mark.parametrize(
    "exit_path", ["finish", "cancel", "reset", "error", "close", "focus_loss"]
)
def test_every_exit_releases_cursor(window, monkeypatch, exit_path):
    from PySide6.QtCore import QEvent

    window.command_button()
    calls = []
    window.cursor_capture = SimpleNamespace(
        active=True, release=lambda **kw: calls.append(kw)
    )
    if exit_path == "finish":
        window.command_button()
    elif exit_path == "cancel":
        window.cancel()
    elif exit_path == "reset":
        window.reset()
    elif exit_path == "error":
        window.tracking_error("lost")
    elif exit_path == "close":
        window.close()
    else:
        monkeypatch.setattr(window, "isActiveWindow", lambda: False)
        window.changeEvent(QEvent(QEvent.Type.ActivationChange))
        assert window.measurement.state == State.ERROR
    assert calls


@pytest.mark.skipif(os.name != "nt", reason="Windows API")
@pytest.mark.desktop
def test_native_cursor_clip_and_release():
    env = dict(os.environ, QT_QPA_PLATFORM="windows")
    script = """
import ctypes as C
from PySide6.QtWidgets import QApplication,QWidget
from cursor_capture import CursorCapture,RECT
a=QApplication([]); w=QWidget(); w.resize(260,180); w.show(); w.activateWindow(); a.processEvents()
c=CursorCapture(); before=RECT(); c.api.GetClipCursor(C.byref(before))
try:
    c.acquire(w)
    current=RECT(); c.api.GetClipCursor(C.byref(current))
    assert c.values(current)==c.values(c.bounds)
    assert c.hide_calls>0
finally:
    c.release(); w.close()
after=RECT(); c.api.GetClipCursor(C.byref(after))
assert c.values(before)==c.values(after)
assert not c.active and c.hide_calls==0
assert a.overrideCursor() is None
print("native-cursor-restored")
"""
    r = subprocess.run(
        [sys.executable, "-c", script],
        cwd=Path(__file__).resolve().parents[1],
        env=env,
        capture_output=True,
        text=True,
        timeout=20,
    )
    assert r.returncode == 0, r.stdout + r.stderr
    assert "native-cursor-restored" in r.stdout
