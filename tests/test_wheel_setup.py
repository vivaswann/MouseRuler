from types import SimpleNamespace
from urllib.parse import parse_qs, urlparse

from PySide6.QtGui import QImage

from input_handler import RawPacket
from mouse_identity import (
    MODEL_HINTS,
    MouseIdentity,
    identity_from_strings,
    model_hint,
    wheel_search_url,
)
from onboarding import WelcomeGuide
from wheel_guide import WHEEL_LESSONS, WheelIllustration
from wheel_page import WheelTurnDialog


def test_receiver_identity_never_becomes_a_mouse_model():
    identity = identity_from_strings(
        r"\\?\HID#VID_046D&PID_C548#private-serial", "USB Receiver"
    )
    assert identity.vendor_id == "046D"
    assert not identity.model_known
    assert "Logitech" in identity.name
    assert model_hint(identity) is None


def test_model_hint_contains_only_source_backed_partial_data():
    identity = identity_from_strings(r"\\?\HID#VID_1532&PID_1234", "Razer Viper V4 Pro")
    hint = model_hint(identity)
    assert hint["steps"] == 24
    assert hint["source"].startswith("https://mysupport.razer.com/")
    assert all("diameter_mm" not in m for m in MODEL_HINTS)
    assert model_hint(MouseIdentity("Razer Naga V2 Pro", True))["steps"] is None


def test_search_sends_model_name_without_private_device_identifiers():
    identity = identity_from_strings(
        r"\\?\HID#VID_046D&PID_C548#secret", "USB Receiver"
    )
    query = parse_qs(urlparse(wheel_search_url(identity)).query)["q"][0]
    assert "Logitech" in query
    assert "secret" not in query and "VID_" not in query and "PID_" not in query


def test_one_turn_counter_rejects_reversal_and_other_devices(app):
    dialog = WheelTurnDialog("mouse")
    dialog.toggle()
    dialog.feed(RawPacket("other", wheel_delta=1200))
    for _ in range(96):
        dialog.feed(RawPacket("mouse", wheel_delta=30))
    dialog.toggle()
    assert dialog.travel / 120 == 24
    assert dialog.use_button.isEnabled()
    dialog.toggle()
    dialog.feed(RawPacket("mouse", wheel_delta=1200))
    dialog.feed(RawPacket("mouse", wheel_delta=-120))
    dialog.toggle()
    assert not dialog.use_button.isEnabled()
    dialog.close()


def test_counter_routes_native_packets_without_affecting_measurement(window):
    window.navigate(3)
    page = window.wheel_page
    page.turn_dialog = WheelTurnDialog("mouse", page)
    page.turn_dialog.isActiveWindow = lambda: True
    page.turn_dialog.toggle()
    window.on_packet(RawPacket("mouse", dx=2000, wheel_delta=240))
    assert page.turn_dialog.travel == 240
    assert page.engine.travel == 0
    assert window.measurement.trajectory.raw_x == 0
    page.turn_dialog.close()
    page.turn_dialog = None


def test_late_identification_cannot_change_an_active_scale(window):
    window.navigate(3)
    page = window.wheel_page
    page.feed(RawPacket("mouse", wheel_delta=120))
    page.increments.setValue(48)
    page.toggle()
    scale = page.engine.active_geometry
    page.identity_ready("other", MouseIdentity("Razer Viper V4 Pro", True))
    page.identity_ready("mouse", MouseIdentity("Razer Viper V4 Pro", True))
    assert page.engine.active_geometry == scale
    assert page.increments.value() == 48
    page.reset()


def test_setup_auto_saves_and_is_collapsed_by_default(window):
    window.navigate(3)
    page = window.wheel_page
    assert not page.setup_widget.isVisible()
    page.feed(RawPacket("mouse", wheel_delta=120))
    page.diameter.setValue(20)
    page.toggle()
    assert page.engine.profiles["mouse"].diameter_mm == 20
    page.reset()


def test_wheel_guide_renders_all_lessons_and_preserves_slide_guide(app):
    guide = WelcomeGuide(
        SimpleNamespace(theme="Light"),
        lessons=WHEEL_LESSONS,
        illustration_type=WheelIllustration,
    )
    for step in range(3):
        guide.step = step
        guide.render_step()
        guide.illustration.resize(800, 300)
        image = QImage(800, 300, QImage.Format.Format_ARGB32)
        image.fill(0)
        guide.illustration.render(image)
        assert image.pixelColor(400, 200).alpha() > 0
        assert guide.title.text() == WHEEL_LESSONS[step][1]
    guide.close()
    original = WelcomeGuide(SimpleNamespace(theme="Light"))
    assert original.title.text() == "One mark. Two edges."
    original.close()
