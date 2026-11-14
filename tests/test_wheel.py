import ctypes as C
import math

import pytest
from PySide6.QtCore import QEvent, Qt
from PySide6.QtTest import QTest

from input_handler import RawPacket
from mouse_input import RAWINPUTHEADER, RAWMOUSE, decode_mouse
from wheel_measurement import WheelGeometry, WheelMeasurement


def wheel(delta, device="wheel-a", **kwargs):
    return RawPacket(device, wheel_delta=delta, **kwargs)


@pytest.mark.parametrize("delta", [-240, -120, -30, 30, 120, 240])
def test_native_signed_wheel_decode(delta):
    h = RAWINPUTHEADER(0, C.sizeof(RAWINPUTHEADER) + C.sizeof(RAWMOUSE), 123, 0)
    m = RAWMOUSE()
    m.buttons.parts.flags = 0x0400
    m.buttons.parts.data = delta & 0xFFFF
    assert decode_mouse(bytes(h) + bytes(m), "mouse", 0).wheel_delta == delta
    m.buttons.parts.flags = 0x0800
    assert decode_mouse(bytes(h) + bytes(m), "mouse", 0).wheel_delta == 0


def selected(tmp_path):
    e = WheelMeasurement(tmp_path / "wheel-geometry.json")
    e.feed(wheel(120))
    return e


def test_no_calibration_required_and_known_full_turn(tmp_path):
    e = selected(tmp_path)
    assert not e.profiles
    e.geometry = WheelGeometry(20, 30, False)
    e.start()
    e.feed(wheel(30 * 120))
    e.finish()
    assert e.completed
    assert e.distance_mm == pytest.approx(math.pi * 20)


def test_fractional_reports_and_backtracking_add_path(tmp_path):
    e = selected(tmp_path)
    e.start()
    for _ in range(4):
        e.feed(wheel(30))
    e.feed(wheel(-120))
    e.finish()
    assert e.net == 0 and e.travel == 240
    assert e.distance_mm == pytest.approx(2 * math.pi)


def test_optical_movement_and_other_devices_cannot_add_distance(tmp_path):
    e = selected(tmp_path)
    e.start()
    e.feed(wheel(0, dx=99999, dy=-99999))
    e.feed(wheel(2400, "other"))
    e.finish()
    assert not e.completed and e.distance_mm is None


def test_geometry_snapshot_and_device_specific_persistence(tmp_path):
    e = selected(tmp_path)
    e.geometry = WheelGeometry(20, 30, False)
    e.save_geometry()
    e.start()
    e.feed(wheel(3600))
    e.geometry = WheelGeometry(40, 30, False)
    e.finish()
    assert e.distance_mm == pytest.approx(20 * math.pi)
    e.feed(wheel(120, "other"))
    assert e.geometry == WheelGeometry()
    assert e.distance_mm is None
    loaded = WheelMeasurement(e.path)
    loaded.feed(wheel(120))
    assert loaded.geometry == WheelGeometry(20, 30, False)


@pytest.mark.parametrize(
    "diameter,increments",
    [(0, 24), (24, 0), (float("nan"), 24), (24, float("inf")), (True, 24)],
)
def test_invalid_geometry_rejected(diameter, increments):
    with pytest.raises(ValueError):
        WheelGeometry(diameter, increments)


def test_failed_save_does_not_replace_saved_geometry(tmp_path, monkeypatch):
    e = selected(tmp_path)
    e.save_geometry()
    previous = e.profiles.copy()
    e.geometry = WheelGeometry(30, 30, False)
    import wheel_measurement

    def fail(*args):
        raise OSError("disk full")

    monkeypatch.setattr(wheel_measurement.os, "replace", fail)
    with pytest.raises(OSError):
        e.save_geometry()
    assert e.profiles == previous


def test_corrupt_geometry_file_uses_labelled_examples(tmp_path):
    path = tmp_path / "wheel.json"
    path.write_text('{"version":1,"profiles":{"mouse":{"diameter_mm":0}}}')
    e = WheelMeasurement(path)
    assert not e.profiles and e.geometry.assumed
    assert "could not be loaded" in e.status


def test_cancel_and_attribute_change_discard_partial_result(tmp_path):
    e = selected(tmp_path)
    e.start()
    e.feed(wheel(1200))
    e.feed(wheel(0, attributes_changed=True))
    assert not e.active and not e.completed and e.distance_mm is None
    e.start()
    e.feed(wheel(1200))
    e.cancel()
    assert e.distance_mm is None


def test_separate_wheel_ui_leaves_optical_state_and_settings_untouched(window, app):
    original_settings = (
        dict(window.settings.profiles),
        dict(window.settings.dpi_profiles),
    )
    window.navigate(3)
    page = window.wheel_page
    page.feed(wheel(120))
    assert "ASSUMED" in page.source.text()
    page.diameter.setValue(25.4 / math.pi)
    page.increments.setValue(24)
    page.confirm_geometry.setChecked(True)
    page.save()
    assert not window.settings.path.exists()
    page.toggle_button.click()
    app.processEvents()
    window.navigate(0)
    assert window.page_index == 3
    page.feed(wheel(2880, dx=9999))
    expected = page.engine.distance_mm
    QTest.keyClick(window, Qt.Key.Key_Return)
    app.processEvents()
    assert not page.engine.active and page.engine.completed
    assert page.values["mm"].text() == f"{expected:.3f}"
    assert page.values["in"].text() == f"{expected / 25.4:.3f}"
    assert window.measurement.trajectory.raw_x == 0
    assert not window.cursor_capture.active
    assert (window.settings.profiles, window.settings.dpi_profiles) == original_settings
    window.navigate(0)
    assert window.page_index == 0


def test_disconnect_and_focus_loss_interrupt_wheel(window, app):
    window.navigate(3)
    page = window.wheel_page
    page.feed(wheel(120))
    page.toggle()
    window.isActiveWindow = lambda: False
    window.changeEvent(QEvent(QEvent.Type.ActivationChange))
    assert not page.engine.active
    page.toggle()
    window.device_removed("wheel-a")
    assert not page.engine.active and not page.engine.device
