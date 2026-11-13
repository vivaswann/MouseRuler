"""Retained PyQtGraph items; drawing is throttled separately from acquisition."""

import pyqtgraph as pg
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget


class TrajectoryCanvas(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        tools = QHBoxLayout()
        self.legend = QLabel("  TRAJECTORY   /   raw sensor coordinates")
        self.legend.setObjectName("eyebrow")
        tools.addWidget(self.legend)
        tools.addStretch()
        self.fit_button = QPushButton("Fit view")
        self.fit_button.setProperty("small", True)
        self.fit_button.setToolTip(
            "Fit the complete trajectory. Wheel to zoom; drag to pan when not recording."
        )
        tools.addWidget(self.fit_button)
        layout.addLayout(tools)
        self.plot = pg.PlotWidget()
        self.plot.setMenuEnabled(False)
        self.plot.hideButtons()
        self.plot.setAntialiasing(True)
        self.plot.setMouseEnabled(x=True, y=True)
        self.plot.setAspectLocked(True)
        self.plot.showGrid(x=True, y=True, alpha=0.12)
        self.plot.setRange(xRange=(-50, 150), yRange=(-65, 65), padding=0)
        self.path = self.plot.plot(pen=pg.mkPen("#568cad", width=2.2))
        self.direct = self.plot.plot(
            pen=pg.mkPen("#9a6e3c", width=2, style=Qt.PenStyle.DashLine)
        )
        self.start = pg.ScatterPlotItem(
            size=12, brush="#269b71", pen=pg.mkPen("#ffffff", width=2)
        )
        self.end = pg.ScatterPlotItem(
            size=12, brush="#d46b64", pen=pg.mkPen("#ffffff", width=2)
        )
        self.current = pg.ScatterPlotItem(size=7, brush="#4687bc", pen=None)
        for item in (self.start, self.end, self.current):
            self.plot.addItem(item)
        self.plot.getPlotItem().getAxis("left").setLabel("Y", units="counts")
        self.plot.getPlotItem().getAxis("bottom").setLabel("X", units="counts")
        layout.addWidget(self.plot, 1)
        self.fit_button.clicked.connect(self.fit)
        self.auto_fit = True
        self.plot.getViewBox().sigRangeChangedManually.connect(self._manual_range)
        self.last_size = -1

    def _manual_range(self, *args):
        self.auto_fit = False

    def theme(self, dark):
        self.plot.setBackground("#1c2025" if dark else "#fafbf9")
        for name in ("left", "bottom"):
            axis = self.plot.getPlotItem().getAxis(name)
            axis.setTextPen("#929da7" if dark else "#85918e")
            axis.setPen("#343c43" if dark else "#e0e5e0")

    def fit(self):
        self.auto_fit = True
        self.plot.enableAutoRange()

    def render_measurement(self, measurement, unit="cm"):
        from distance_calculator import UNITS
        from measurement_state import State

        divisor = UNITS[unit] if measurement.physical_units else 1.0
        points = measurement.trajectory.points / divisor
        active = measurement.state != State.IDLE
        self.path.setData(
            points[:, 0] if active else [], points[:, 1] if active else []
        )
        self.start.setData([0] if active else [], [0] if active else [])
        self.current.setData(
            [points[-1, 0]] if active else [], [points[-1, 1]] if active else []
        )
        complete = measurement.state == State.COMPLETED
        self.end.setData(
            [points[-1, 0]] if complete else [], [points[-1, 1]] if complete else []
        )
        self.direct.setData(
            [0, points[-1, 0]] if complete else [],
            [0, points[-1, 1]] if complete else [],
        )
        suffix = unit if measurement.physical_units else "counts"
        for name, label in (("left", "Y"), ("bottom", "X")):
            self.plot.getPlotItem().getAxis(name).setLabel(label, units=suffix)
            self.plot.getPlotItem().getAxis(name).enableAutoSIPrefix(False)
        self.plot.setMouseEnabled(
            x=measurement.state != State.RECORDING,
            y=measurement.state != State.RECORDING,
        )
        self.legend.setText(f"  TRAJECTORY   /   {suffix} · Y up")
        if self.auto_fit and len(points) > 1:
            self.plot.enableAutoRange()
        elif len(points) == 1:
            span = 5 if measurement.physical_units else 100
            self.plot.setRange(xRange=(-span, span), yRange=(-span, span), padding=0)
