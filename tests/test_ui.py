import json

from input_handler import RawPacket as P
from measurement_state import State


def test_initial_no_fabricated_measurement(window):
    assert window.direct_value.text() == "—"
    assert window.cal_banner.isVisible()
    assert "sensor counts" in window.result_unit.text()
    assert not window.export_button.isEnabled()
    assert window.direct_value.height() >= 80


def test_button_workflow_and_canvas(window, app):
    window.start_button.click()
    window.router.feed(P("test-mouse", 30, 40, timestamp=1), allowed=False)
    window.router.feed(P("test-mouse", 30, -40, timestamp=2), allowed=False)
    window.finish_button.setEnabled(True)
    window.finish_button.click()
    window.refresh()
    app.processEvents()
    assert window.measurement.state == State.COMPLETED
    assert window.direct_value.text() == "60.00"
    assert window.path_value.text() == "100.00 counts"
    assert len(window.canvas.direct.xData) == 2
    assert window.export_button.isEnabled()


def test_double_click_workflow(window):
    for t, b in [(1, 1), (1.01, 2), (1.1, 1), (1.11, 2)]:
        window.router.feed(P("test-mouse", buttons=b, timestamp=t))
    assert window.measurement.state == State.RECORDING
    window.router.feed(P("test-mouse", 300, 400, timestamp=1.5))
    for t, b in [(2, 1), (2.01, 2), (2.1, 1), (2.11, 2), (2.2, 1), (2.21, 2)]:
        window.router.feed(P("test-mouse", buttons=b, timestamp=t))
    window.refresh()
    assert window.measurement.state == State.COMPLETED
    assert window.direct_value.text() == "500.00"


def test_calibration_workflow_then_physical_units(window):
    window.navigate(1)
    window.command_button()
    window.router.feed(P("test-mouse", 1000, 0, timestamp=1), False)
    window.command_button()
    window.add_trial()
    assert len(window.calibration.coefficients) == 1
    window.add_trial()  # must not count the same traverse twice
    assert len(window.calibration.coefficients) == 1
    window.save_calibration()
    assert window.page_index == 0
    assert window.settings.path.exists()
    window.command_button()
    window.router.feed(P("test-mouse", 600, 800, timestamp=2), False)
    window.command_button()
    window.refresh()
    assert window.direct_value.text() == "10.00"
    assert window.result_unit.text() == "cm"
    window.change_unit("in")
    window.refresh()
    assert window.direct_value.text() == "3.94"


def test_navigation_during_recording_blocked(window):
    window.command_button()
    window.navigate(1)
    assert window.page_index == 0
    assert window.measurement.state == State.RECORDING
    window.cancel()
    window.navigate(1)
    assert window.page_index == 1


def test_dark_mode_and_diagnostics(window, app):
    window.theme_combo.setCurrentText("Dark")
    window.toggle_diagnostics()
    window.refresh()
    app.processEvents()
    assert window.settings.theme == "Dark"
    assert window.diagnostics.isVisible()
    data = json.loads(window.diagnostics.toPlainText())
    assert not data["raw_input_registered"]
    assert data["calibration_mm_per_count"] is None


def test_tracking_error_preserves_partial_and_does_not_finish(window):
    window.command_button()
    window.router.feed(P("test-mouse", 100, 0), False)
    window.tracking_error("disconnected")
    window.refresh()
    assert window.measurement.state == State.ERROR
    assert not window.export_button.isEnabled()
    assert "partial" in window.result_hint.text()
    assert window.measurement.trajectory.distances.direct == 100


def test_keyboard_shortcuts(window, app):
    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest

    window.activateWindow()
    window.setFocus()
    app.processEvents()
    QTest.keyClick(window, Qt.Key.Key_Return)
    app.processEvents()
    assert window.measurement.state == State.RECORDING
    QTest.keyClick(window, Qt.Key.Key_Escape)
    app.processEvents()
    assert window.measurement.state == State.IDLE
    window.command_button()
    window.command_button()
    QTest.keyClick(window, Qt.Key.Key_R)
    app.processEvents()
    assert window.measurement.state == State.IDLE


def test_save_failure_does_not_claim_saved(window, monkeypatch):
    window.navigate(1)
    window.command_button()
    window.router.feed(P("test-mouse", 1000, 0), False)
    window.command_button()
    window.add_trial()

    def fail():
        raise OSError("read-only")

    monkeypatch.setattr(window.settings, "save", fail)
    window.save_calibration()
    assert not window.settings.profiles
    assert "not saved" in window.message.text()
