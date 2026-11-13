"""Explicit software self-test for the shipped executable; never shows fake data."""

import json
import tempfile
import traceback
from pathlib import Path

from input_handler import RawPacket
from measurement_state import State
from settings import Settings


def run(app, report_path):
    from main import MainWindow

    report_path = Path(report_path).resolve()
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report = {
        "kind": "packaged software self-test",
        "synthetic_measurement_data": True,
        "physical_accuracy_tested": False,
        "checks": [],
    }
    window = None

    def check(name, condition):
        if not condition:
            raise AssertionError(name)
        report["checks"].append(name)

    try:
        with tempfile.TemporaryDirectory(prefix="MouseMeasure-test-") as temp:
            window = MainWindow(Settings(Path(temp) / "settings.json"))
            check(
                "Native Windows Raw Input registration",
                window.native and window.native.registered,
            )
            report["enumerated_mouse_devices"] = len(window.native.enumerate_mice())
            check(
                "Native device enumeration",
                isinstance(report["enumerated_mouse_devices"], int),
            )
            check(
                "No fabricated initial measurement", window.direct_value.text() == "—"
            )
            # Synthetic input stays in this hidden test instance and temporary profile.
            window.native.stop()
            window._requires_raw = False

            def send(t, buttons=0, x=0, y=0):
                window.router.feed(RawPacket("synthetic-self-test", x, y, buttons, t))

            for t, b in [(1, 1), (1.01, 2), (1.1, 1), (1.11, 2)]:
                send(t, b)
            check(
                "Double-left-click starts once",
                window.measurement.state == State.RECORDING,
            )
            send(1.2, x=30, y=40)
            send(1.3, x=30, y=-40)
            for t, b in [(2, 1), (2.01, 2), (2.1, 1), (2.11, 2), (2.2, 1), (2.21, 2)]:
                send(t, b)
            window.refresh()
            app.processEvents()
            check(
                "Double-left-click finishes; third click ignored",
                window.measurement.state == State.COMPLETED,
            )
            check(
                "Separate direct and travelled distances",
                window.direct_value.text() == "60.00"
                and window.path_value.text() == "100.00 counts",
            )
            check(
                "Full trajectory and direct connecting line",
                len(window.canvas.path.xData) == 3
                and len(window.canvas.direct.xData) == 2,
            )
            window.navigate(1)
            window.command_button()
            send(3, x=1000)
            window.command_button()
            window.add_trial()
            window.save_calibration()
            check("Calibration saved", window.settings.path.exists())
            reloaded = Settings(window.settings.path)
            check(
                "Calibration survives reload",
                reloaded.profiles["synthetic-self-test"].mm_per_count == 0.1,
            )
            window.command_button()
            send(4, x=30, y=40)
            send(4.1, x=30, y=-40)
            window.command_button()
            window.refresh()
            check(
                "Calibrated physical unit conversion",
                window.direct_value.text() == "0.60"
                and window.result_unit.text() == "cm",
            )
            window.change_unit("in")
            window.refresh()
            check("Inch unit conversion", window.direct_value.text() == "0.24")
            window.change_theme("Dark")
            window.navigate(2)
            window.refresh()
            app.processEvents()
            check(
                "Dark settings page renders",
                window.settings.theme == "Dark" and window.pages.currentIndex() == 2,
            )
            check(
                "Diagnostics contain calibration and state",
                window.diagnostic_data()["calibration_mm_per_count"] == 0.1,
            )
            window.navigate(0)
            window.command_button()
            window.cancel()
            check("Cancellation resets state", window.measurement.state == State.IDLE)
            window.save_dpi("synthetic-self-test", 1600)
            window.command_button()
            send(5, x=960, y=1280)
            window.command_button()
            window.refresh()
            check(
                "DPI provides physical lengths without calibration",
                abs(window.measurement.trajectory.distances.direct - 25.4) < 1e-8
                and window.measurement.scale_source == "dpi",
            )
            check(
                "Four-unit direct and path display",
                window.all_unit_values["mm"][0].text() == "25.4000"
                and window.all_unit_values["in"][1].text() == "1.0000",
            )
            check(
                "DPI estimate is labelled honestly",
                "DPI-based estimate" in window.accuracy_label.text(),
            )
            from dpi_detection import detect_mouse_dpi

            result = detect_mouse_dpi("synthetic-self-test")
            check(
                "Unsupported DPI detection has no fabricated value", result.dpi is None
            )
            window.reset()
            check("Reset leaves cursor released", not window.cursor_capture.active)
            window.close()
            window = None
        report["status"] = "passed"
        report["passed"] = len(report["checks"])
        exit_code = 0
    except Exception:
        report["status"] = "failed"
        report["error"] = traceback.format_exc()
        exit_code = 1
    finally:
        if window:
            window.close()
    report_path.write_text(
        json.dumps(report, indent=2, allow_nan=False), encoding="utf-8"
    )
    return exit_code
