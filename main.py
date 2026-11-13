"""MouseMeasure — Windows sensor-count measurement utility."""

import argparse
import json
import logging
import sys
import time
from logging.handlers import RotatingFileHandler
from pathlib import Path

import pyqtgraph as pg
from PySide6.QtCore import QEvent, QPropertyAnimation, Qt, QTimer
from PySide6.QtGui import QFont, QIcon, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QAbstractSpinBox,
    QApplication,
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QFrame,
    QGraphicsOpacityEffect,
    QGridLayout,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPlainTextEdit,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from calibration import CalibrationSession
from cursor_capture import CursorCapture
from distance_calculator import UNITS, from_mm
from dpi_detection import detect_mouse_dpi, dpi_scale
from input_handler import InputRouter
from measurement_state import Measurement, State
from settings import Settings
from visualization import TrajectoryCanvas

VERSION = "1.2.0"


def label(text, name=None, wrap=False):
    widget = QLabel(text)
    if name:
        widget.setObjectName(name)
    widget.setWordWrap(wrap)
    return widget


def button(text, callback, primary=False):
    widget = QPushButton(text)
    widget.setCursor(Qt.CursorShape.PointingHandCursor)
    if primary:
        widget.setObjectName("primary")
    widget.clicked.connect(callback)
    return widget


class MainWindow(QMainWindow):
    def __init__(self, settings=None, enable_raw=True):
        super().__init__()
        self.settings = settings or Settings()
        self.measurement = Measurement()
        self.calibration = CalibrationSession()
        self.page_index = 0
        self.native = None
        self._requires_raw = enable_raw
        self.cursor_capture = CursorCapture()
        self.dpi_detections = {}
        self._dpi_dialog_open = False
        self.heading = None
        self.cal_trial_added = False
        self._dirty = True
        self._last_state = None
        self._last_diag = 0.0
        self.setWindowTitle("MouseMeasure")
        self.setMinimumSize(960, 730)
        self.resize(1280, 850)
        self.router = InputRouter(self.measurement, self.command)
        self.router.detector.max_motion = self.settings.click_motion_counts
        self._build_ui()
        self.state_opacity = QGraphicsOpacityEffect(self.state_label)
        self.state_label.setGraphicsEffect(self.state_opacity)
        self.state_animation = QPropertyAnimation(self.state_opacity, b"opacity", self)
        self.state_animation.setDuration(240)
        self._shortcuts()
        self.apply_theme()
        if enable_raw:
            try:
                from mouse_input import RawInput

                self.native = RawInput()
                self.router.detector.interval = self.native.double_click_interval
                self.native.packet.connect(self.on_packet)
                self.native.error.connect(self.tracking_error)
                self.native.removed.connect(self.device_removed)
                self.native.start(int(self.winId()), QApplication.instance())
                mice = self.native.enumerate_mice()
                self.hardware_status.setText(
                    f"Windows Raw Input · {len(mice)} mouse device(s)"
                )
            except Exception as exc:
                self.tracking_error(f"Cannot activate Windows Raw Input: {exc}")
        else:
            self.hardware_status.setText("Software test · physical input disabled")
        if self.settings.warning:
            self.notice(self.settings.warning)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh)
        self.timer.start(33)
        QApplication.instance().aboutToQuit.connect(self.cursor_capture.release)
        self.refresh()

    def _build_ui(self):
        root = QWidget()
        self.setCentralWidget(root)
        outer = QVBoxLayout(root)
        outer.setContentsMargins(32, 20, 32, 20)
        outer.setSpacing(16)
        nav = QHBoxLayout()
        mark = label("m↗", "brandmark")
        mark.setFixedSize(44, 40)
        mark.setAlignment(Qt.AlignmentFlag.AlignCenter)
        nav.addWidget(mark)
        nav.addWidget(label("MouseMeasure", "brand"))
        nav.addStretch()
        self.nav_buttons = []
        for i, text in enumerate(("Measurement", "Calibration", "Settings")):
            btn = button(text, lambda checked=False, index=i: self.navigate(index))
            btn.setObjectName("nav")
            btn.setCheckable(True)
            btn.setChecked(i == 0)
            nav.addWidget(btn)
            self.nav_buttons.append(btn)
        outer.addLayout(nav)
        guide_button = button("Guide", self.show_guide)
        guide_button.setObjectName("nav")
        nav.addWidget(guide_button)
        line = QFrame()
        line.setObjectName("divider")
        line.setFixedHeight(1)
        outer.addWidget(line)
        self.pages = QStackedWidget()
        self.pages.addWidget(self._measurement_page())
        self.pages.addWidget(self._calibration_page())
        self.pages.addWidget(self._settings_page())
        outer.addWidget(self.pages, 1)
        self.message = label("", "message", True)
        self.message.hide()
        outer.addWidget(self.message)
        self.diagnostics = QPlainTextEdit()
        self.diagnostics.setReadOnly(True)
        self.diagnostics.setAccessibleName("Raw input diagnostics")
        self.diagnostics.setMaximumHeight(155)
        self.diagnostics.hide()
        outer.addWidget(self.diagnostics)
        bottom = QHBoxLayout()
        self.hardware_status = label("Activating Windows Raw Input…", "muted")
        bottom.addWidget(self.hardware_status)
        bottom.addStretch()
        self.diag_button = button("Diagnostics", self.toggle_diagnostics)
        self.diag_button.setProperty("small", True)
        bottom.addWidget(self.diag_button)
        outer.addLayout(bottom)

    def _measurement_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 8, 0, 0)
        layout.setSpacing(18)
        heading = QHBoxLayout()
        titles = QVBoxLayout()
        titles.addWidget(label("From point to point.", "title"))
        titles.addWidget(
            label(
                "Double-click to start. Move freely. Double-click to finish.",
                "subtitle",
            )
        )
        heading.addLayout(titles)
        heading.addStretch()
        self.state_label = label("●  READY", "state")
        self.state_label.setFixedHeight(34)
        heading.addWidget(self.state_label)
        layout.addLayout(heading)
        self.cal_banner = QFrame()
        self.cal_banner.setObjectName("banner")
        banner = QHBoxLayout(self.cal_banner)
        self.cal_banner_text = label(
            "Enter your mouse DPI to measure now. Calibrate later to refine the scale.",
            wrap=True,
        )
        banner.addWidget(self.cal_banner_text, 1)
        banner.addWidget(button("Set mouse DPI", self.configure_dpi))
        banner.addWidget(button("Calibrate  →", lambda: self.navigate(1)))
        layout.addWidget(self.cal_banner)
        content = QHBoxLayout()
        content.setSpacing(28)
        self.canvas = TrajectoryCanvas()
        canvas_column = QVBoxLayout()
        canvas_column.addWidget(self.canvas, 1)
        all_units = QFrame()
        all_units.setObjectName("banner")
        units_grid = QGridLayout(all_units)
        units_grid.setContentsMargins(12, 8, 12, 8)
        units_grid.setHorizontalSpacing(18)
        units_grid.setVerticalSpacing(4)
        self.all_unit_values = {}
        units_grid.addWidget(label("Direct", "metric"), 1, 0)
        units_grid.addWidget(label("Path", "muted"), 2, 0)
        for column, unit in enumerate(UNITS, 1):
            units_grid.addWidget(label(unit, "eyebrow"), 0, column)
            self.all_unit_values[unit] = (label("—", "metric"), label("—", "muted"))
            for row, widget in enumerate(self.all_unit_values[unit], 1):
                widget.setTextInteractionFlags(
                    Qt.TextInteractionFlag.TextSelectableByMouse
                )
                units_grid.addWidget(widget, row, column)
            units_grid.setColumnStretch(column, 1)
        canvas_column.addWidget(all_units)
        content.addLayout(canvas_column, 1)
        result = QFrame()
        result.setObjectName("result")
        result.setFixedWidth(295)
        right = QVBoxLayout(result)
        right.setContentsMargins(20, 20, 20, 20)
        right.setSpacing(8)
        right.addWidget(label("DIRECT DISTANCE", "eyebrow"))
        self.direct_value = label("—", "distance")
        self.direct_value.setMinimumHeight(80)
        self.direct_value.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        right.addWidget(self.direct_value)
        self.result_unit = label("sensor counts", "unit")
        right.addWidget(self.result_unit)
        self.result_hint = label(
            "The straight line between your two points.", "muted", True
        )
        right.addWidget(self.result_hint)
        right.addSpacing(2)
        self.path_value = self._metric(right, "Travelled path")
        self.x_value = self._metric(right, "Horizontal · X")
        self.y_value = self._metric(right, "Vertical · Y")
        right.addStretch()
        self.accuracy_label = label(
            "Accuracy not established.\nCalibrate before measuring in physical units.",
            "muted",
            True,
        )
        right.addWidget(self.accuracy_label)
        self.export_button = button("Export measurement", self.export_measurement)
        content.addWidget(result)
        layout.addLayout(content, 1)
        legend = QHBoxLayout()
        legend.addWidget(
            label(
                "● Start     ● End       ━ Travelled path       ┄ Direct distance",
                "muted",
            )
        )
        legend.addStretch()
        legend.addWidget(label("Wheel to zoom · Drag to pan after finishing", "muted"))
        layout.addLayout(legend)
        controls = QHBoxLayout()
        self.start_button = button("Start measurement", self.command_button, True)
        self.finish_button = button("Finish", self.command_button)
        self.reset_button = button("Reset", self.reset)
        controls.addWidget(self.start_button)
        controls.addWidget(self.finish_button)
        controls.addWidget(self.reset_button)
        controls.addWidget(self.export_button)
        controls.addStretch()
        controls.addWidget(
            label("↵ Start / finish     Esc Cancel     R Reset", "muted")
        )
        layout.addLayout(controls)
        layout.addWidget(
            label(
                "Keep the mouse facing the same direction and flat on the surface. Measure at its sensor, not its front edge.",
                "muted",
                True,
            )
        )
        return page

    def _metric(self, parent_layout, title):
        row = QHBoxLayout()
        row.addWidget(label(title, "muted"))
        row.addStretch()
        value = label("—", "metric")
        row.addWidget(value)
        parent_layout.addLayout(row)
        return value

    def show_guide(self):
        if self.measurement.state == State.RECORDING:
            self.notice("Finish or cancel before opening the guide.")
            return
        from onboarding import WelcomeGuide

        guide = WelcomeGuide(self.settings, self)
        if guide.exec() == WelcomeGuide.DialogCode.Accepted:
            self.settings.show_guide = guide.every_time.isChecked()
            self.persist_settings()

    def _calibration_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 8, 0, 0)
        layout.setSpacing(20)
        layout.addWidget(label("Give movement a scale.", "title"))
        layout.addWidget(
            label(
                "A ruler, your mouse, and a straight traverse. Repeat three times for a scale repeatability estimate.",
                "subtitle",
                True,
            )
        )
        content = QHBoxLayout()
        content.setSpacing(36)
        instructions = QVBoxLayout()
        for number, title, body in (
            (
                "01",
                "Choose a reference",
                "Use a long ruler distance, such as 100 mm. Keep the same DPI, mouse, surface, and orientation for calibration and measurement.",
            ),
            (
                "02",
                "Record one straight traverse",
                "Align a mark on the mouse with the ruler start. Double-click, move along the ruler without rotating or lifting, then double-click at the endpoint. Only the recorded motion counts.",
            ),
            (
                "03",
                "Add the trial and save",
                "Enter the distance actually traversed, add the trial, then repeat. Save when ready. One trial enables units; repeated trials estimate scale repeatability only.",
            ),
        ):
            instructions.addWidget(label(number, "step"))
            instructions.addWidget(label(title, "section"))
            instructions.addWidget(label(body, "muted", True))
            instructions.addSpacing(14)
        instructions.addStretch()
        content.addLayout(instructions, 1)
        panel = QFrame()
        panel.setObjectName("result")
        panel.setMinimumWidth(390)
        form = QVBoxLayout(panel)
        form.setContentsMargins(28, 28, 28, 28)
        form.setSpacing(16)
        form.addWidget(label("RULER CALIBRATION", "eyebrow"))
        form.addWidget(label("Reference distance", "section"))
        row = QHBoxLayout()
        self.reference = QDoubleSpinBox()
        self.reference.setRange(0.001, 1_000_000)
        self.reference.setDecimals(3)
        self.reference.setValue(100)
        self.reference.setAccessibleName("Known reference distance")
        self.ref_unit = QComboBox()
        self.ref_unit.addItems(UNITS)
        row.addWidget(self.reference, 1)
        row.addWidget(self.ref_unit)
        form.addLayout(row)
        self.cal_record = button("Record ruler traverse", self.command_button, True)
        form.addWidget(self.cal_record)
        form.addWidget(button("Cancel traverse", self.cancel))
        self.cal_motion = label(
            "Waiting for a traverse.\nDouble-click or press Enter to begin.",
            "subtitle",
            True,
        )
        form.addWidget(self.cal_motion)
        self.add_trial_button = button("Add this trial", self.add_trial)
        form.addWidget(self.add_trial_button)
        self.cal_summary = label("No new calibration trials yet.", "muted", True)
        form.addWidget(self.cal_summary)
        form.addStretch()
        self.save_cal_button = button(
            "Save calibration & measure", self.save_calibration, True
        )
        form.addWidget(self.save_cal_button)
        content.addWidget(panel, 1)
        layout.addLayout(content, 1)
        self.existing_cal = label("", "muted", True)
        layout.addWidget(self.existing_cal)
        return page

    def _settings_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 8, 0, 0)
        layout.setSpacing(14)
        layout.addWidget(label("Make it yours.", "title"))
        dpi_row = QHBoxLayout()
        dpi_row.addWidget(label("Mouse DPI", "section"))
        self.dpi_status = label(
            "Move your mouse, then set its hardware DPI.", "muted", True
        )
        dpi_row.addWidget(self.dpi_status, 1)
        dpi_row.addWidget(button("Detect / set DPI", self.configure_dpi))
        layout.addLayout(dpi_row)
        row = QHBoxLayout()
        row.addWidget(label("Appearance", "section"))
        row.addStretch()
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["Light", "Dark"])
        self.theme_combo.setCurrentText(self.settings.theme)
        self.theme_combo.currentTextChanged.connect(self.change_theme)
        row.addWidget(self.theme_combo)
        row.addSpacing(32)
        row.addWidget(label("Measurement unit", "section"))
        self.unit_combo = QComboBox()
        self.unit_combo.addItems(UNITS)
        self.unit_combo.setCurrentText(self.settings.unit)
        self.unit_combo.currentTextChanged.connect(self.change_unit)
        row.addWidget(self.unit_combo)
        layout.addLayout(row)
        layout.addSpacing(12)
        tolerance_row = QHBoxLayout()
        tolerance_row.addWidget(label("Double-click movement tolerance", "section"))
        tolerance_row.addStretch()
        self.click_tolerance = QDoubleSpinBox()
        self.click_tolerance.setDecimals(0)
        self.click_tolerance.setRange(4, 2000)
        self.click_tolerance.setSuffix(" counts")
        self.click_tolerance.setValue(self.settings.click_motion_counts)
        self.click_tolerance.setToolTip(
            "Default: 40 raw counts between clicks. Increase if a high-DPI mouse rejects small click jitter. Larger values admit more movement between unrelated clicks."
        )
        self.click_tolerance.valueChanged.connect(self.change_click_tolerance)
        tolerance_row.addWidget(self.click_tolerance)
        layout.addLayout(tolerance_row)
        layout.addWidget(
            label(
                "While recording, the cursor is hidden and confined to the graph. Double-click or press Enter to finish; Escape cancels and releases it. Switching to another app stops recording and releases the cursor.",
                "muted",
                True,
            )
        )
        layout.addWidget(label("Optional heading sensor", "section"))
        row = QHBoxLayout()
        self.imu_port = QLineEdit()
        self.imu_port.setPlaceholderText("Serial port, e.g. COM3")
        self.imu_port.setAccessibleName("Optional IMU serial port")
        row.addWidget(self.imu_port)
        self.imu_button = button("Connect IMU", self.toggle_imu)
        row.addWidget(self.imu_button)
        layout.addLayout(row)
        self.imu_status = label(
            "Disconnected · fixed mouse orientation required", "muted", True
        )
        layout.addWidget(self.imu_status)
        layout.addWidget(
            label(
                'Experimental: 115200 baud, ≥20 Hz JSON lines {"yaw_deg": 12.5}. CCW yaw in the Y-up frame; zeroed at each measurement start. Missing or stale heading stops recording. Ruler calibration always uses fixed orientation.',
                "muted",
                True,
            )
        )
        layout.addWidget(label("What an ordinary mouse can tell you", "section"))
        layout.addWidget(
            label(
                "Raw Input bypasses Windows pointer acceleration and screen boundaries. Calibration converts relative sensor counts into length. The mouse cannot detect rotation, lift-off, a DPI change, or missed motion on a poor surface. Keep its heading fixed and its sensor in contact. Do not use these measurements for safety-critical work.",
                "muted",
                True,
            )
        )
        layout.addWidget(
            label(
                "A heading sensor can rotate local vectors into a common frame, but yaw drift, timing, and the offset between the IMU and optical sensor still affect accuracy. No total accuracy claim is made. The smallest mouse-only aid is a sliding orientation guide that prevents rotation.",
                "muted",
                True,
            )
        )
        layout.addStretch()
        row = QHBoxLayout()
        row.addWidget(button("Export diagnostics", self.export_diagnostics))
        row.addStretch()
        row.addWidget(
            label(f"MouseMeasure {VERSION} · Local only · No telemetry", "muted")
        )
        layout.addLayout(row)
        return page

    def _shortcuts(self):
        self.shortcuts = []
        for key, callback in (
            ("Return", self.keyboard_command),
            ("Enter", self.keyboard_command),
            ("Escape", self.cancel),
            ("R", self.keyboard_reset),
        ):
            shortcut = QShortcut(QKeySequence(key), self)
            shortcut.setAutoRepeat(False)
            shortcut.activated.connect(callback)
            self.shortcuts.append(shortcut)

    def keyboard_command(self):
        if self.page_index < 2 and not isinstance(
            QApplication.focusWidget(), (QLineEdit, QAbstractSpinBox)
        ):
            self.command_button()

    def keyboard_reset(self):
        if self.page_index < 2 and not isinstance(
            QApplication.focusWidget(), (QLineEdit, QAbstractSpinBox)
        ):
            self.reset()

    def navigate(self, index):
        if self.measurement.state == State.RECORDING:
            self.notice("Finish the measurement or press Escape before changing pages.")
            self.nav_buttons[index].setChecked(False)
            self.nav_buttons[self.page_index].setChecked(True)
            return
        self.router.detector.reset()
        if index != self.page_index and (index == 1 or self.page_index == 1):
            self.reset()
        self.page_index = index
        self.pages.setCurrentIndex(index)
        for i, btn in enumerate(self.nav_buttons):
            btn.setChecked(i == index)
        self._dirty = True

    def _click_allowed(self):
        if self.page_index == 2 or QApplication.activeModalWidget():
            return False
        if self.cursor_capture.active:
            # Captured clicks are measurement commands even if the invisible
            # pointer is at a graph edge. Screen coordinates never measure motion.
            return self.isActiveWindow()
        # Pointer position is used ONLY to exclude controls from commands.
        # It is never used to estimate sensor movement or a physical coordinate.
        from PySide6.QtGui import QCursor

        position = QCursor.pos()
        if self.frameGeometry().contains(position) and not self.rect().contains(
            self.mapFromGlobal(position)
        ):
            return False  # non-client title bar, maximize/close buttons
        target = QApplication.widgetAt(position)
        current = target
        while current is not None:
            if isinstance(
                current,
                (
                    QPushButton,
                    QComboBox,
                    QAbstractSpinBox,
                    QLineEdit,
                    QCheckBox,
                    QPlainTextEdit,
                ),
            ):
                return False
            if current is self:
                break
            current = current.parentWidget()
        if self.settings.background_clicks:
            return True
        if target is None or not (target is self or self.isAncestorOf(target)):
            return False
        if self.native:
            return self.native.user32.GetForegroundWindow() == int(self.winId())
        return self.isActiveWindow()

    def on_packet(self, packet):
        self.router.feed(packet, self._click_allowed())
        if self.measurement.state != State.RECORDING:
            self.cursor_capture.release()
        if (
            self.measurement.state == State.RECORDING
            or packet.buttons
            or self.measurement.state == State.ERROR
        ):
            self._dirty = True

    def configure_dpi(self, checked=False, device=None):
        if self._dpi_dialog_open or self.measurement.state == State.RECORDING:
            return
        device = device or self.measurement.device or self.router.last_device
        if not device:
            self.notice("Move the physical mouse first, then choose Set mouse DPI.")
            return
        self._dpi_dialog_open = True
        self.router.detector.reset()
        try:
            raw_handle = next(
                (
                    h
                    for h, n in getattr(self.native, "devices", {}).items()
                    if n == device
                ),
                None,
            )
            detection = detect_mouse_dpi(device, raw_handle=raw_handle)
            self.dpi_detections[device] = detection
            stored = self.settings.dpi_profiles.get(device)
            initial = stored["dpi"] if stored else (detection.dpi or 800)
            value, accepted = QInputDialog.getDouble(
                self,
                "Mouse hardware DPI",
                detection.explanation
                + "\n\nEnter the current hardware DPI (not display scaling or Windows pointer speed)."
                "\nThe initial 800 value is only an editable example when no value is known."
                "\nChanging DPI clears the previous ruler calibration for this mouse.",
                initial,
                1,
                1_000_000,
                3,
            )
            if accepted:
                source = (
                    "HID reported (confirmed)"
                    if detection.dpi is not None and abs(value - detection.dpi) < 0.001
                    else "manual"
                )
                self.save_dpi(device, value, source)
        finally:
            self._dpi_dialog_open = False
            self.router.detector.reset()

    def save_dpi(self, device, value, source="manual"):
        dpi_scale(value)
        if not device or source not in ("manual", "HID reported (confirmed)"):
            raise ValueError("Invalid mouse or DPI source.")
        if self.measurement.state == State.RECORDING:
            raise ValueError("Finish or cancel before changing mouse DPI.")
        old_dpi = self.settings.dpi_profiles.get(device)
        old_cal = self.settings.profiles.get(device)
        self.settings.dpi_profiles[device] = {"dpi": value, "source": source}
        if old_dpi is None or old_dpi["dpi"] != value:
            self.settings.profiles.pop(device, None)
        try:
            self.settings.save()
        except OSError as exc:
            if old_dpi is None:
                self.settings.dpi_profiles.pop(device, None)
            else:
                self.settings.dpi_profiles[device] = old_dpi
            if old_cal:
                self.settings.profiles[device] = old_cal
            self.notice(f"DPI could not be saved: {exc}")
            return
        if (
            old_dpi is None or old_dpi["dpi"] != value
        ) and self.calibration.device == device:
            self.calibration = CalibrationSession()
            self.cal_summary.setText(
                "DPI changed. Record fresh ruler trials for this setting."
            )
        self.reset()
        self.router.last_device = device
        self.notice(
            f"Saved {value:g} DPI. Position the mouse at your start point and double-click. Calibration is optional."
        )
        self._dirty = True

    def command_button(self):
        self.router.detector.reset()
        self.command(self.measurement.device or self.router.last_device)

    def command(self, device):
        if self.page_index == 2:
            return
        if self._requires_raw and not (self.native and self.native.registered):
            self.notice(
                "Windows Raw Input is unavailable. See Diagnostics before measuring."
            )
            return
        if self._requires_raw and self.isVisible() and not self.isActiveWindow():
            self.notice("Bring MouseMeasure to the foreground before recording.")
            return
        if self.measurement.state == State.RECORDING:
            self.measurement.finish()
            self.cursor_capture.release()
        else:
            profile = (
                self.settings.profiles.get(device) if self.page_index == 0 else None
            )
            dpi_profile = (
                self.settings.dpi_profiles.get(device) if self.page_index == 0 else None
            )
            if (
                self.page_index == 0
                and device
                and not profile
                and not dpi_profile
                and self._requires_raw
            ):
                self.configure_dpi(device=device)
                return
            try:
                if self.heading and self.page_index == 0:
                    self.heading.poll()
                    self.heading.set_zero()
                self.measurement.heading_source = (
                    self.heading if self.page_index == 0 else None
                )
                scale = (
                    profile.mm_per_count
                    if profile
                    else (dpi_scale(dpi_profile["dpi"]) if dpi_profile else None)
                )
                self.measurement.start(
                    device, scale, "calibration" if profile else "dpi"
                )
                if self._requires_raw and self.isVisible():
                    area = (
                        self.canvas.plot.viewport()
                        if self.page_index == 0
                        else self.cal_motion
                    )
                    self.cursor_capture.acquire(area)
                self.cal_trial_added = False
                self.canvas.auto_fit = True
                self.message.hide()
            except (ValueError, RuntimeError) as exc:
                self.cursor_capture.release()
                if self.measurement.state == State.RECORDING:
                    self.tracking_error(str(exc))
                else:
                    self.notice(str(exc))
        self._dirty = True

    def reset(self):
        self.cursor_capture.release()
        self.measurement.reset()
        self.router.detector.reset()
        self.canvas.auto_fit = True
        self.cal_trial_added = False
        self.message.hide()
        self._dirty = True

    def cancel(self):
        self.cursor_capture.release()
        if self.measurement.state == State.RECORDING:
            self.measurement.cancel()
            self.router.detector.reset()
            self.notice("Measurement cancelled. No result was saved.")
            self._dirty = True

    def add_trial(self):
        m = self.measurement
        if m.state != State.COMPLETED or self.cal_trial_added:
            return
        t = m.trajectory
        try:
            self.calibration.add_trial(
                self.reference.value(),
                self.ref_unit.currentText(),
                t.raw_x,
                t.raw_y,
                t.raw_path,
                m.device,
            )
            self.cal_trial_added = True
            profile = self.calibration.profile()
            sem = profile.relative_scale_sem
            detail = (
                "Scale uncertainty needs repeated trials."
                if sem is None
                else f"Scale SEM: {sem * 100:.3f}% (repeatability only)."
            )
            self.cal_summary.setText(
                f"{len(profile.trials)} trial(s) · {profile.mm_per_count:.8f} mm/count\n{detail}\nTotal physical uncertainty remains unvalidated."
            )
            self.message.hide()
        except ValueError as exc:
            self.notice(str(exc))
        self._dirty = True

    def save_calibration(self):
        if self.measurement.state == State.RECORDING:
            return
        try:
            profile = self.calibration.profile()
            old = self.settings.profiles.get(profile.device)
            self.settings.profiles[profile.device] = profile
            try:
                self.settings.save()
            except OSError:
                if old:
                    self.settings.profiles[profile.device] = old
                else:
                    del self.settings.profiles[profile.device]
                raise
            self.navigate(0)
            self.notice(
                "Calibration saved. Place the mouse at your start point and double-click."
            )
        except (ValueError, OSError) as exc:
            self.notice(f"Calibration not saved: {exc}")

    def notice(self, text):
        self.message.setText(text)
        self.message.show()

    def tracking_error(self, text):
        self.cursor_capture.release()
        logging.error(text)
        self.router.error(text)
        if self.measurement.state != State.ERROR:
            self.measurement.fail(text)
        self.notice(text)
        self._dirty = True

    def device_removed(self, device):
        if device == self.measurement.device:
            self.tracking_error(
                "Selected mouse disconnected. Reconnect, reset, and check calibration."
            )
        if device == self.router.last_device:
            self.router.last_device = ""

    def change_theme(self, theme):
        self.settings.theme = theme
        self.apply_theme()
        self.persist_settings()

    def change_unit(self, unit):
        self.settings.unit = unit
        self.persist_settings()
        self._dirty = True

    def set_background(self, checked):
        self.settings.background_clicks = checked
        self.router.detector.reset()

    def change_click_tolerance(self, value):
        self.settings.click_motion_counts = int(value)
        self.router.detector.max_motion = int(value)
        self.router.detector.reset()
        self.persist_settings()

    def persist_settings(self):
        try:
            self.settings.save()
        except OSError as exc:
            self.notice(f"Could not save settings: {exc}")

    def toggle_imu(self):
        if self.measurement.state == State.RECORDING:
            self.notice("Finish or cancel before changing the heading sensor.")
            return
        if self.heading:
            self.heading.close()
            self.heading = None
            self.measurement.heading_source = None
            self.imu_button.setText("Connect IMU")
            self.imu_status.setText("Disconnected · fixed mouse orientation required")
            return
        try:
            from heading_input import SerialHeadingSource

            self.heading = SerialHeadingSource(self.imu_port.text().strip())
            self.imu_button.setText("Disconnect IMU")
            self.imu_status.setText("Connected · waiting for yaw JSON lines")
        except Exception as exc:
            self.notice(f"Cannot connect IMU: {exc}")

    def refresh(self):
        if self.cursor_capture.active:
            if self.measurement.state != State.RECORDING:
                self.cursor_capture.release()
            else:
                try:
                    self.cursor_capture.update()
                except RuntimeError as exc:
                    self.tracking_error(str(exc))
        if self.heading:
            try:
                self.heading.poll()
                self.heading.heading(time.monotonic())
                self.imu_status.setText(
                    f"Receiving yaw · {self.heading.value * 180 / 3.14159265:.1f}° · experimental"
                )
            except RuntimeError as exc:
                self.imu_status.setText(str(exc))
                if (
                    self.measurement.state == State.RECORDING
                    and self.measurement.heading_source
                ):
                    self.tracking_error(str(exc))
        m = self.measurement
        if self._dirty:
            self._dirty = False
            names = {
                State.IDLE: "●  READY",
                State.RECORDING: "●  RECORDING",
                State.COMPLETED: "●  COMPLETE",
                State.ERROR: "●  INPUT ERROR",
            }
            self.state_label.setText(names[m.state])
            if m.state != self._last_state:
                self._last_state = m.state
                self.state_animation.stop()
                self.state_animation.setStartValue(0.45)
                self.state_animation.setEndValue(1.0)
                self.state_animation.start()
            self.state_label.setProperty("recording", m.state == State.RECORDING)
            self.state_label.style().unpolish(self.state_label)
            self.state_label.style().polish(self.state_label)
            values = m.trajectory.distances
            unit = self.settings.unit if m.physical_units else "counts"
            divisor = UNITS[unit] if m.physical_units else 1.0
            active = m.state in (
                State.RECORDING,
                State.COMPLETED,
                State.ERROR,
            ) and bool(m.device)
            fmt = lambda v: f"{v / divisor:,.2f}" if active else "—"
            self.direct_value.setText(fmt(values.direct))
            # Keep long metre/mm/count results inside the result panel.
            self.direct_value.setStyleSheet(
                f"font-size: {62 if len(self.direct_value.text()) < 8 else 38}px;"
            )
            self.result_unit.setText(unit if m.physical_units else "sensor counts")
            for widget, value in (
                (self.path_value, values.path),
                (self.x_value, values.horizontal),
                (self.y_value, values.vertical),
            ):
                widget.setText(f"{fmt(value)} {unit}" if active else "—")
            profile = self.settings.profiles.get(m.device or self.router.last_device)
            dpi_profile = self.settings.dpi_profiles.get(
                m.device or self.router.last_device
            )
            if dpi_profile:
                self.dpi_status.setText(
                    f"{dpi_profile['dpi']:g} DPI · {dpi_profile['source']}"
                    + (" · ruler calibrated" if profile else " · approximate")
                )
            elif profile:
                self.dpi_status.setText("Ruler calibrated · DPI entry not required")
            else:
                self.dpi_status.setText(
                    "Hardware DPI unknown · Detect / set DPI before measuring"
                )
            self.cal_banner.setVisible(not bool(profile))
            self.cal_banner_text.setText(
                f"Using {dpi_profile['dpi']:g} DPI · approximate lengths. Calibrate later to refine the scale."
                if dpi_profile
                else "Enter your mouse DPI to measure now. Calibrate later to refine the scale."
            )
            for display_unit, (
                direct_label,
                path_label,
            ) in self.all_unit_values.items():
                direct_label.setText(
                    f"{from_mm(values.direct, display_unit):,.4f}"
                    if active and m.physical_units
                    else "—"
                )
                path_label.setText(
                    f"{from_mm(values.path, display_unit):,.4f}"
                    if active and m.physical_units
                    else "—"
                )
            if m.state == State.ERROR:
                self.result_hint.setText(
                    "Interrupted · partial trace only. Reset before trying again."
                )
            else:
                self.result_hint.setText(
                    "Live displacement from your start."
                    if m.state == State.RECORDING
                    else "The straight line between your two points."
                )
            if profile:
                sem = profile.relative_scale_sem
                if sem is None:
                    text = "Repeat trials to estimate scale SEM."
                elif active and m.calibrated:
                    component = from_mm(values.direct * sem, self.settings.unit)
                    text = f"Scale-only SEM: ±{component:.3g} {self.settings.unit}."
                else:
                    text = f"Scale repeatability SEM: {sem * 100:.3f}%."
                self.accuracy_label.setText(
                    f"Calibrated · {len(profile.trials)} ruler trial(s)\n{text}\nTotal accuracy not yet validated."
                )
            elif m.scale_source == "dpi" or dpi_profile:
                self.accuracy_label.setText(
                    "DPI-based estimate · not ruler calibrated.\nCalibrate to refine the scale.\nPhysical uncertainty is unknown."
                )
            else:
                self.accuracy_label.setText(
                    "Uncalibrated · sensor counts only.\nPhysical uncertainty is unknown."
                )
            self.canvas.render_measurement(m, self.settings.unit)
            rec = m.state == State.RECORDING
            self.start_button.setEnabled(not rec)
            self.finish_button.setEnabled(rec)
            self.export_button.setEnabled(m.state == State.COMPLETED)
            self.cal_record.setText(
                "Finish ruler traverse" if rec else "Record ruler traverse"
            )
            self.add_trial_button.setEnabled(
                m.state == State.COMPLETED and not self.cal_trial_added
            )
            self.save_cal_button.setEnabled(
                bool(self.calibration.coefficients) and not rec
            )
            if self.page_index == 1:
                t = m.trajectory
                self.cal_motion.setText(
                    f"{names[m.state]}\nNet: {(t.raw_x * t.raw_x + t.raw_y * t.raw_y) ** 0.5:,.0f} counts · path: {t.raw_path:,.0f} counts"
                )
            self.existing_cal.setText(
                f"{len(self.settings.profiles)} saved mouse profile(s). Calibration belongs to a device and DPI; repeat whenever either or the surface changes."
            )
        if self.diagnostics.isVisible() and time.monotonic() - self._last_diag > 0.2:
            self._last_diag = time.monotonic()
            self.diagnostics.setPlainText(json.dumps(self.diagnostic_data(), indent=2))

    def diagnostic_data(self):
        m = self.measurement
        p = self.settings.profiles.get(m.device or self.router.last_device)
        return dict(
            version=VERSION,
            state=m.state.value,
            raw_input_registered=bool(self.native and self.native.registered),
            device=m.device or self.router.last_device or "No identified mouse yet",
            raw_counts=dict(
                x=m.trajectory.raw_x, y=m.trajectory.raw_y, path=m.trajectory.raw_path
            ),
            raw_counts_since_launch=dict(
                x=self.router.counts_x, y=self.router.counts_y
            ),
            packets=self.router.packets,
            samples=m.trajectory.size - 1,
            calibration_mm_per_count=p.mm_per_count if p else None,
            calibration_trials=len(p.trials) if p else 0,
            dpi_profile=self.settings.dpi_profiles.get(
                m.device or self.router.last_device
            ),
            scale_source=m.scale_source,
            mm_per_count=m.scale if m.physical_units else None,
            cursor_captured=self.cursor_capture.active,
            last_input_event=self.router.last_event,
            errors=self.router.errors,
            measurement_error=m.error,
            background_commands=self.settings.background_clicks,
            double_click_interval_ms=self.router.detector.interval * 1000,
            double_click_motion_tolerance=self.router.detector.max_motion,
            heading="experimental serial yaw"
            if self.heading
            else "fixed orientation assumed",
        )

    def toggle_diagnostics(self):
        self.diagnostics.setVisible(not self.diagnostics.isVisible())
        self._last_diag = 0
        self.refresh()

    def export_diagnostics(self):
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Save diagnostics locally",
            "MouseMeasure-diagnostics.json",
            "JSON (*.json)",
        )
        if filename:
            self.write_json(filename, self.diagnostic_data())

    def export_measurement(self):
        if self.measurement.state != State.COMPLETED:
            return
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Save measurement locally",
            "MouseMeasure-measurement.json",
            "JSON (*.json)",
        )
        if filename:
            m = self.measurement
            v = m.trajectory.distances
            data = dict(
                diagnostics=self.diagnostic_data(),
                coordinate_unit="mm" if m.physical_units else "counts",
                direct=v.direct,
                travelled_path=v.path,
                horizontal=v.horizontal,
                vertical=v.vertical,
                points=m.trajectory.points.tolist(),
                all_units={
                    u: dict(direct=from_mm(v.direct, u), path=from_mm(v.path, u))
                    for u in UNITS
                }
                if m.physical_units
                else None,
                accuracy="Total physical uncertainty is unvalidated; fixed orientation / no lift required.",
            )
            self.write_json(filename, data)

    def write_json(self, filename, data):
        try:
            Path(filename).write_text(
                json.dumps(data, indent=2, allow_nan=False), encoding="utf-8"
            )
            self.notice(f"Saved to {filename}")
        except (OSError, ValueError) as exc:
            self.notice(f"Could not save file: {exc}")

    def apply_theme(self):
        from theme import application_stylesheet

        dark = self.settings.theme == "Dark"
        self.setStyleSheet(application_stylesheet(dark))
        self.canvas.theme(dark)

    def changeEvent(self, event):
        super().changeEvent(event)
        if event.type() == QEvent.Type.ActivationChange and hasattr(
            self, "cursor_capture"
        ):
            if self.cursor_capture.active and not self.isActiveWindow():
                self.cursor_capture.release(restore_previous=False)
                self.tracking_error(
                    "Recording interrupted: MouseMeasure lost focus. Cursor released; reset and measure again."
                )

    def closeEvent(self, event):
        self.cursor_capture.release()
        self.timer.stop()
        if self.native:
            self.native.stop()
        if self.heading:
            self.heading.close()
        event.accept()


def main():
    parser = argparse.ArgumentParser(
        description="MouseMeasure — calibrated Windows Raw Input measurement"
    )
    parser.add_argument(
        "--windowed",
        action="store_true",
        help="Launch in a resizable window instead of maximized",
    )
    parser.add_argument(
        "--self-test",
        action="store_true",
        help="Run a hidden software self-test, then exit; not a physical accuracy test",
    )
    parser.add_argument("--report", help="JSON output path required with --self-test")
    args = parser.parse_args()
    pg.setConfigOptions(antialias=True)
    app = QApplication(sys.argv[:1])
    app.setApplicationName("MouseMeasure")
    app.setOrganizationName("MouseMeasure")
    app.setFont(QFont("Segoe UI", 10))
    settings = Settings()
    try:
        settings.path.parent.mkdir(parents=True, exist_ok=True)
        handler = RotatingFileHandler(
            settings.path.parent / "MouseMeasure.log",
            maxBytes=2_000_000,
            backupCount=1,
            encoding="utf-8",
        )
        logging.basicConfig(level=logging.INFO, handlers=[handler])
    except OSError:
        logging.basicConfig(level=logging.INFO)

    def exception_hook(typ, value, tb):
        logging.exception("Unhandled application error", exc_info=(typ, value, tb))
        if app.activeWindow() and isinstance(app.activeWindow(), MainWindow):
            app.activeWindow().tracking_error(f"Application error: {value}")
        else:
            sys.__excepthook__(typ, value, tb)

    sys.excepthook = exception_hook
    if args.self_test:
        if not args.report:
            parser.error("--self-test requires --report PATH")
        from self_test import run

        return run(app, args.report)
    window = MainWindow(settings)
    icon_path = (
        Path(getattr(sys, "_MEIPASS", Path(__file__).parent))
        / "assets"
        / "MouseMeasure.ico"
    )
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))
    if args.windowed:
        window.show()
    else:
        window.showMaximized()
    if settings.show_guide:
        QTimer.singleShot(200, window.show_guide)
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
