"""Separate wheel-measurement page; optical measurement state stays independent."""

from PySide6.QtCore import QEvent, QObject, QRunnable, Qt, QThreadPool, Signal, Slot
from PySide6.QtGui import QDesktopServices, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QDoubleSpinBox,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from mouse_identity import (
    MODEL_HINTS,
    identify_mouse,
    identity_from_strings,
    model_hint,
    wheel_search_url,
)
from wheel_measurement import WheelGeometry, WheelMeasurement


class IdentitySignals(QObject):
    ready = Signal(str, object)


class IdentityWorker(QRunnable):
    def __init__(self, device):
        super().__init__()
        self.device = device
        self.signals = IdentitySignals()

    def run(self):
        try:
            identity = identify_mouse(self.device)
        except (OSError, ValueError):
            identity = identity_from_strings(self.device)
        self.signals.ready.emit(self.device, identity)


class WheelTurnDialog(QDialog):
    def __init__(self, device, parent=None):
        super().__init__(parent)
        self.device = device
        self.active = False
        self.travel = self.net = 0
        self.setWindowTitle("Count one wheel turn")
        self.resize(580, 340)
        layout = QVBoxLayout(self)
        self.title = QLabel("Find the scroll increments in one revolution.")
        self.title.setWordWrap(True)
        self.title.setObjectName("section")
        layout.addWidget(self.title)
        text = QLabel(
            "With the mouse lifted, use a removable mark on the wheel to recognize one full turn. Start counting, turn it exactly once in one direction, then stop. This sets rotation steps only; it does not determine wheel diameter."
        )
        text.setWordWrap(True)
        layout.addWidget(text)
        self.count = QLabel("0 increments")
        self.count.setObjectName("section")
        layout.addWidget(self.count)
        self.message = QLabel(
            "Use the same wheel mode you will measure with. Disable free-spin."
        )
        self.message.setWordWrap(True)
        layout.addWidget(self.message)
        row = QHBoxLayout()
        self.toggle_button = QPushButton("Start counting (Enter)")
        self.toggle_button.clicked.connect(self.toggle)
        self.use_button = QPushButton("Use this step count")
        self.use_button.setEnabled(False)
        self.use_button.clicked.connect(self.accept)
        for button in (self.toggle_button, self.use_button):
            button.setAutoDefault(False)
            row.addWidget(button)
        layout.addLayout(row)
        self.shortcut = QShortcut(QKeySequence("Return"), self)
        self.shortcut.setAutoRepeat(False)
        self.shortcut.activated.connect(self.toggle)

    def toggle(self):
        if self.active:
            self.active = False
            valid = self.travel >= 120 and self.travel == abs(self.net)
            self.use_button.setEnabled(valid)
            self.message.setText(
                "Use this value only if you completed exactly one full revolution."
                if valid
                else "Try again: turn the wheel in one direction for exactly one revolution."
            )
        else:
            self.travel = self.net = 0
            self.active = True
            self.use_button.setEnabled(False)
            self.message.setText("Counting… stop after exactly one full turn.")
        self.count.setText(f"{self.travel / 120:g} increments")
        self.toggle_button.setText(
            "Stop counting (Enter)" if self.active else "Count again (Enter)"
        )

    def feed(self, packet):
        if self.active and packet.device == self.device:
            if packet.absolute or packet.attributes_changed:
                self.interrupt("Mouse input changed. Count discarded.")
                return
            self.net += packet.wheel_delta
            self.travel += abs(packet.wheel_delta)
            self.count.setText(f"{self.travel / 120:g} increments")

    def interrupt(self, reason):
        self.active = False
        self.travel = self.net = 0
        self.use_button.setEnabled(False)
        self.count.setText("0 increments")
        self.message.setText(reason)
        self.toggle_button.setText("Start counting (Enter)")

    def changeEvent(self, event):
        super().changeEvent(event)
        if (
            event.type() == QEvent.Type.ActivationChange
            and self.active
            and not self.isActiveWindow()
        ):
            self.interrupt("Counting interrupted by focus loss. Try again.")


class WheelPage(QWidget):
    def __init__(self, path, parent=None, hardware_enabled=True):
        super().__init__(parent)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.engine = WheelMeasurement(path)
        self.hardware_enabled = hardware_enabled
        self.identities = {}
        self.worker = None
        self.turn_dialog = None
        self.setup_dirty = False
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 8, 0, 0)
        layout.setSpacing(14)
        self.add_label(layout, "WHEEL MEASUREMENT", "eyebrow")
        self.add_label(layout, "Roll the wheel along your object.", "title")
        self.add_label(
            layout,
            "1  Roll once to select your mouse     2  Start and roll along the surface     3  Press Enter to finish",
            "subtitle",
        )
        self.device_label = self.add_label(layout, "", "muted")
        tools = QHBoxLayout()
        self.guide_button = self.add_button(
            tools, "How to roll · animated guide", self.show_guide
        )
        self.setup_button = self.add_button(
            tools,
            "Wheel setup",
            lambda: self.setup_widget.setVisible(self.setup_button.isChecked()),
        )
        self.setup_button.setCheckable(True)
        tools.addStretch()
        layout.addLayout(tools)
        self.distance = self.add_label(layout, "—", "distance")
        self.distance.setMinimumHeight(90)
        self.add_label(layout, "ROLLED PATH · GEOMETRY-BASED ESTIMATE", "eyebrow")
        grid = QGridLayout()
        self.values = {}
        for index, unit in enumerate(("mm", "cm", "m", "in")):
            grid.addWidget(QLabel(unit), 0, index)
            value = QLabel("—")
            value.setObjectName("section")
            self.values[unit] = value
            grid.addWidget(value, 1, index)
        layout.addLayout(grid)
        self.counts = self.add_label(layout, "", "muted")
        self.source = self.add_label(layout, "", "message")
        self.setup_widget = QWidget()
        setup = QVBoxLayout(self.setup_widget)
        setup.setContentsMargins(0, 0, 0, 0)
        self.model_combo = QComboBox()
        self.model_combo.addItem("Use detected mouse / generic wheel")
        for model in MODEL_HINTS:
            self.model_combo.addItem(model["name"])
        self.model_combo.currentIndexChanged.connect(self.select_model)
        setup.addWidget(self.model_combo)
        self.hint_label = self.add_label(
            setup,
            "Wheel diameter usually is not published. Use your own dimensions or continue with a clearly labelled rough estimate.",
            "muted",
        )
        lookup = QHBoxLayout()
        self.add_button(lookup, "Find wheel specifications online ↗", self.search_specs)
        self.source_button = self.add_button(
            lookup, "Manufacturer source ↗", self.open_source
        )
        self.source_button.setEnabled(False)
        lookup.addStretch()
        setup.addLayout(lookup)
        dimensions = QHBoxLayout()
        dimensions.addWidget(QLabel("Wheel diameter"))
        self.diameter = self.spin(1, 100, 24, 2, " mm")
        dimensions.addWidget(self.diameter)
        dimensions.addWidget(QLabel("Scroll increments per full turn"))
        self.increments = self.spin(1, 10000, 24, 2, "")
        dimensions.addWidget(self.increments)
        self.save_button = self.add_button(dimensions, "Save wheel settings", self.save)
        setup.addLayout(dimensions)
        self.add_button(setup, "Count one full turn · no ruler needed", self.count_turn)
        self.confirm_geometry = QCheckBox(
            "I supplied these values for my mouse (otherwise use example geometry)"
        )
        self.confirm_geometry.toggled.connect(self.geometry_changed)
        setup.addWidget(self.confirm_geometry)
        self.diameter.valueChanged.connect(self.geometry_changed)
        self.increments.valueChanged.connect(self.geometry_changed)
        layout.addWidget(self.setup_widget)
        self.setup_widget.hide()
        self.status = self.add_label(layout, "", "subtitle")
        actions = QHBoxLayout()
        self.toggle_button = self.add_button(
            actions, "Start wheel measurement", self.toggle
        )
        self.toggle_button.setObjectName("primary")
        self.add_button(actions, "Reset", self.reset)
        actions.addStretch()
        layout.addLayout(actions)
        self.add_label(
            layout,
            "Enter starts / stops · Escape cancels · R resets · Keep this window in front.\nClick outside a number field before using Enter.",
            "muted",
        )
        layout.addStretch()
        self.add_label(
            layout,
            "Keep the wheel in contact without slipping. Disable free-spin. Backtracking adds to length.\nNo ruler calibration is required. Example wheel dimensions give a rough estimate; improve them in Wheel setup.",
            "subtitle",
        )
        self.refresh()

    def showEvent(self, event):
        super().showEvent(event)
        QApplication.instance().installEventFilter(self)

    def hideEvent(self, event):
        QApplication.instance().removeEventFilter(self)
        super().hideEvent(event)

    @staticmethod
    def spin(low, high, value, decimals, suffix):
        spin = QDoubleSpinBox()
        spin.setRange(low, high)
        spin.setDecimals(decimals)
        spin.setValue(value)
        spin.setSuffix(suffix)
        spin.setMinimumWidth(110)
        return spin

    @staticmethod
    def add_label(layout, text, name):
        label = QLabel(text)
        label.setObjectName(name)
        label.setWordWrap(True)
        layout.addWidget(label)
        return label

    @staticmethod
    def add_button(layout, text, callback):
        button = QPushButton(text)
        button.clicked.connect(callback)
        layout.addWidget(button)
        return button

    def eventFilter(self, target, event):
        if event.type() == QEvent.Type.Wheel and isinstance(target, QWidget):
            return self.isVisible() and (target is self or self.isAncestorOf(target))
        return False

    def geometry_changed(self, *_):
        self.engine.geometry = WheelGeometry(
            self.diameter.value(),
            self.increments.value(),
            not self.confirm_geometry.isChecked(),
        )
        self.setup_dirty = True
        self.refresh()

    def feed(self, packet):
        previous = self.engine.device
        self.engine.feed(packet)
        if previous != self.engine.device:
            for widget, value in (
                (self.diameter, self.engine.geometry.diameter_mm),
                (self.increments, self.engine.geometry.increments_per_turn),
            ):
                widget.blockSignals(True)
                widget.setValue(value)
                widget.blockSignals(False)
            self.confirm_geometry.blockSignals(True)
            self.confirm_geometry.setChecked(not self.engine.geometry.assumed)
            self.confirm_geometry.blockSignals(False)
            self.setup_dirty = False
            self.model_combo.setCurrentIndex(0)
            if self.engine.device in self.identities:
                self.identity_ready(
                    self.engine.device, self.identities[self.engine.device]
                )
            elif self.hardware_enabled:
                self.worker = IdentityWorker(self.engine.device)
                self.worker.signals.ready.connect(self.identity_ready)
                QThreadPool.globalInstance().start(self.worker)
        if packet.wheel_delta or packet.absolute or packet.attributes_changed:
            self.refresh()

    def shutdown(self):
        QApplication.instance().removeEventFilter(self)
        self.interrupt("Wheel recording stopped because MouseRuler closed.")

    def toggle(self):
        try:
            if not self.engine.active and self.setup_dirty:
                self.engine.save_geometry()
                self.setup_dirty = False
            self.engine.finish() if self.engine.active else self.engine.start()
        except ValueError as exc:
            self.engine.status = str(exc)
        self.setFocus()
        self.refresh()

    def reset(self):
        self.engine.cancel("Ready for another wheel measurement.")
        self.refresh()

    def save(self):
        try:
            self.engine.save_geometry()
            self.setup_dirty = False
        except (ValueError, OSError) as exc:
            self.engine.status = f"Wheel settings not saved: {exc}"
        self.refresh()

    def interrupt(self, reason):
        if self.turn_dialog:
            self.turn_dialog.interrupt(reason)
        if self.engine.active:
            self.engine.cancel(reason)
            self.refresh()

    def refresh(self):
        e = self.engine
        identity = self.identities.get(e.device)
        device = (
            identity.name
            if identity
            else "Mouse selected"
            if e.device
            else "Roll the wheel to select your mouse"
        )
        self.device_label.setText(f"{device} · wheel input only · no mouse DPI needed")
        distance = e.distance_mm
        self.distance.setText("—" if distance is None else f"{distance / 10:,.2f} cm")
        for unit, divisor in (("mm", 1), ("cm", 10), ("m", 1000), ("in", 25.4)):
            self.values[unit].setText(
                "—" if distance is None else f"{distance / divisor:,.3f}"
            )
        self.counts.setText(
            f"Raw wheel units: {e.travel:,} travelled / {e.net:+,} signed · {e.travel / 120:g} scroll increments"
        )
        geometry = e.active_geometry if e.active or e.completed else e.geometry
        source = (
            "ASSUMED GEOMETRY · rough estimate only"
            if geometry.assumed
            else "USER-SPECIFIED GEOMETRY · accuracy unverified"
        )
        self.source.setText(
            f"{source}\n{geometry.diameter_mm:g} mm wheel diameter · {geometry.increments_per_turn:g} increments per turn"
        )
        self.status.setText(e.status)
        self.toggle_button.setText(
            "Stop wheel measurement (Enter)" if e.active else "Start wheel measurement"
        )
        for widget in (self.diameter, self.increments, self.confirm_geometry):
            widget.setEnabled(not e.active)
        self.save_button.setEnabled(not e.active and bool(e.device))
        self.setup_button.setEnabled(not e.active)
        self.setup_widget.setEnabled(not e.active)
        self.guide_button.setEnabled(not e.active)
        self.model_combo.setEnabled(not e.active)

    @Slot(str, object)
    def identity_ready(self, device, identity):
        self.identities[device] = identity
        if device != self.engine.device:
            return
        hint = model_hint(identity)
        if (
            hint
            and not self.engine.active
            and not self.setup_dirty
            and device not in self.engine.profiles
        ):
            self.apply_hint(hint)
        self.refresh()

    def current_hint(self):
        if self.model_combo.currentIndex() > 0:
            return MODEL_HINTS[self.model_combo.currentIndex() - 1]
        identity = self.identities.get(self.engine.device)
        return model_hint(identity) if identity else None

    def select_model(self, *_):
        self.apply_hint(self.current_hint())

    def apply_hint(self, hint):
        self.source_button.setEnabled(bool(hint))
        self.hint_label.setText(
            hint["note"]
            if hint
            else "No complete wheel geometry is verified for this device. The mouse body’s dimensions are not its wheel diameter."
        )
        if hint and hint["steps"] and not self.engine.active:
            self.increments.setValue(hint["steps"])

    def search_specs(self):
        from PySide6.QtCore import QUrl

        from mouse_identity import MouseIdentity

        hint = self.current_hint()
        identity = (
            MouseIdentity(hint["name"], True)
            if hint
            else self.identities.get(
                self.engine.device, identity_from_strings(self.engine.device)
            )
        )
        QDesktopServices.openUrl(QUrl(wheel_search_url(identity)))

    def open_source(self):
        from PySide6.QtCore import QUrl

        hint = self.current_hint()
        if hint:
            QDesktopServices.openUrl(QUrl(hint["source"]))

    def show_guide(self):
        from types import SimpleNamespace

        from onboarding import WelcomeGuide
        from wheel_guide import WHEEL_LESSONS, WheelIllustration

        if self.engine.active:
            return
        settings = getattr(self.window(), "settings", SimpleNamespace(theme="Light"))
        guide = WelcomeGuide(
            settings, self, lessons=WHEEL_LESSONS, illustration_type=WheelIllustration
        )
        guide.setWindowTitle("How to use the wheel ruler")
        guide.every_time.hide()
        guide.exec()

    def count_turn(self):
        if self.engine.active:
            return
        if not self.engine.device:
            self.engine.status = "Roll the wheel once to select your mouse first."
            self.refresh()
            return
        self.turn_dialog = WheelTurnDialog(self.engine.device, self)
        try:
            if self.turn_dialog.exec() == QDialog.DialogCode.Accepted:
                self.increments.setValue(self.turn_dialog.travel / 120)
                self.engine.status = "One-turn count applied. Check wheel diameter, then Start to save this setup automatically."
                self.refresh()
        finally:
            self.turn_dialog = None
