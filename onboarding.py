"""Animated, deliberately illustrative instructions for fixed-heading measurement."""

from math import pi, sin

from PySide6.QtCore import QElapsedTimer, QPointF, QRectF, Qt, QTimer
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

LESSONS = (
    (
        "01 / ALIGN",
        "One mark. Two edges.",
        "Use the centre of your scroll wheel or a fixed mark on the mouse. "
        "Line that same mark up with the first edge, then the second. A ruler or "
        "straightedge makes the alignment easier.",
    ),
    (
        "02 / MOVE",
        "The path can bend. The mouse should not turn.",
        "Double-click to start. Slide the mouse to the other edge, keeping its nose "
        "pointing the same way and its sensor flat. Double-click again to finish. "
        "The cursor hides while recording; Enter also finishes and Escape cancels.",
    ),
    (
        "03 / KEEP IT CONSISTENT",
        "Small habits make a better measurement.",
        "Keep the same heading, body mark, DPI, and surface. Never lift or pivot "
        "mid-measurement. The sensor is underneath the mouse: a wheel or body mark "
        "works because its fixed offset cancels when the mouse does not rotate.",
    ),
)


class MeasurementIllustration(QWidget):
    """A timed drawing, separate from the input and measurement engines."""

    def __init__(self, dark=False, parent=None):
        super().__init__(parent)
        self.dark = dark
        self.step = 0
        self.paused = False
        self.pause_elapsed = 0
        self.setMinimumHeight(290)
        self.setAccessibleName("Illustrated measuring instructions")
        self.setAccessibleDescription(
            "Use one body mark at both edges; slide without rotating or lifting."
        )
        self.clock = QElapsedTimer()
        self.clock.start()
        self.timer = QTimer(self)
        self.timer.setInterval(33)
        self.timer.timeout.connect(self.update)

    def showEvent(self, event):
        super().showEvent(event)
        if not self.paused:
            self.timer.start()

    def hideEvent(self, event):
        self.timer.stop()
        super().hideEvent(event)

    def set_step(self, step):
        self.step = step
        self.clock.restart()
        self.pause_elapsed = 0
        self.update()

    def set_paused(self, paused):
        self.paused = paused
        self.pause_elapsed = self.clock.elapsed()
        self.timer.stop() if paused else self.timer.start()

    @staticmethod
    def mouse(painter, x, y, angle=0, color="#315e49"):
        painter.save()
        painter.translate(x, y)
        painter.rotate(angle)
        painter.setPen(QPen(QColor(color), 2))
        painter.setBrush(QColor("#e1ebe1"))
        painter.drawRoundedRect(QRectF(-26, -48, 52, 94), 25, 25)
        painter.drawLine(QPointF(0, -46), QPointF(0, -7))
        painter.setBrush(QColor(color))
        painter.drawRoundedRect(QRectF(-4, -34, 8, 19), 4, 4)
        painter.restore()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.scale(self.width() / 800, self.height() / 300)
        ink = QColor("#dbe8dd" if self.dark else "#315441")
        muted = QColor("#a6b3ac" if self.dark else "#6f8275")
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#202d28" if self.dark else "#edf2eb"))
        painter.drawRoundedRect(QRectF(0, 0, 800, 300), 18, 18)
        painter.setFont(QFont("Segoe UI", 10))
        if self.step == 2:
            for index, (title, caption, rotation) in enumerate(
                (
                    ("DO · SLIDE", "Same heading, same mark", 0),
                    ("DON’T · PIVOT", "Turning changes the frame", 35),
                    ("DON’T · LIFT", "Air movement is not recorded", 0),
                )
            ):
                x = 140 + index * 260
                self.mouse(painter, x - 26, 136)
                self.mouse(
                    painter,
                    x + 48,
                    112 if index == 2 else 136,
                    rotation,
                    "#b45e55" if index else "#315e49",
                )
                painter.setPen(QPen(ink if index == 0 else QColor("#bd7065"), 2))
                painter.drawLine(QPointF(x - 60, 199), QPointF(x + 85, 199))
                painter.setPen(ink)
                painter.drawText(
                    QRectF(x - 115, 220, 230, 24), Qt.AlignmentFlag.AlignCenter, title
                )
                painter.setPen(muted)
                painter.drawText(
                    QRectF(x - 115, 246, 230, 24), Qt.AlignmentFlag.AlignCenter, caption
                )
            return

        start, end = 140, 660
        painter.setBrush(QColor("#34443a" if self.dark else "#d9e3d5"))
        painter.drawRoundedRect(QRectF(start, 42, end - start, 42), 6, 6)
        painter.setPen(ink)
        painter.drawText(
            QRectF(220, 48, 360, 28),
            Qt.AlignmentFlag.AlignCenter,
            "THE SURFACE YOU’RE MEASURING",
        )
        painter.setPen(QPen(muted, 1, Qt.PenStyle.DashLine))
        for x in (start, end):
            painter.drawLine(QPointF(x, 31), QPointF(x, 253))

        elapsed = self.pause_elapsed if self.paused else self.clock.elapsed()
        phase = min((elapsed % 7200) / 5400, 1.0) if self.step else 0
        current_x = start + (end - start) * phase
        current_y = 157 + sin(phase * pi) * sin(phase * pi * 3) * 30
        if self.step:
            path = QPainterPath(QPointF(start, 132))
            for index in range(1, 101):
                t = phase * index / 100
                path.lineTo(
                    start + (end - start) * t, 132 + sin(t * pi) * sin(t * pi * 3) * 30
                )
            painter.setPen(QPen(QColor("#668fa9"), 2.5))
            painter.drawPath(path)
            painter.setPen(QPen(QColor("#b49365"), 1.5, Qt.PenStyle.DashLine))
            painter.drawLine(QPointF(start, 132), QPointF(current_x, current_y - 25))
        self.mouse(painter, current_x, current_y)
        painter.setPen(QPen(QColor("#73956a"), 2))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(QPointF(current_x, current_y - 25), 13, 13)
        painter.setPen(ink)
        painter.drawText(
            QRectF(35, 262, 210, 25), Qt.AlignmentFlag.AlignCenter, "START · SAME MARK"
        )
        painter.drawText(
            QRectF(555, 262, 210, 25),
            Qt.AlignmentFlag.AlignCenter,
            "FINISH · SAME MARK",
        )
        painter.setPen(muted)
        painter.drawText(
            QRectF(240, 223, 320, 24),
            Qt.AlignmentFlag.AlignCenter,
            "Keep the mouse facing ↑ throughout",
        )


class WelcomeGuide(QDialog):
    def __init__(self, settings, parent=None):
        super().__init__(parent)
        self.settings = settings
        self.step = 0
        self.setWindowTitle("A quick guide to MouseRuler")
        self.resize(880, 640)
        self.setMinimumSize(760, 600)
        self.setModal(True)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 25, 30, 25)
        layout.setSpacing(15)
        self.counter = QLabel()
        self.counter.setObjectName("eyebrow")
        self.title = QLabel()
        self.title.setObjectName("title")
        self.title.setWordWrap(True)
        self.body = QLabel()
        self.body.setWordWrap(True)
        self.body.setMinimumHeight(64)
        self.body.setObjectName("subtitle")
        layout.addWidget(self.counter)
        layout.addWidget(self.title)
        layout.addWidget(self.body)
        self.illustration = MeasurementIllustration(settings.theme == "Dark")
        layout.addWidget(self.illustration, 1)
        info = QHBoxLayout()
        caption = QLabel("Illustration only · no live measurement data")
        caption.setObjectName("muted")
        info.addWidget(caption)
        info.addStretch()
        pause = QCheckBox("Pause animation")
        pause.toggled.connect(self.illustration.set_paused)
        info.addWidget(pause)
        layout.addLayout(info)
        self.every_time = QCheckBox("Show this guide at every launch")
        layout.addWidget(self.every_time)
        actions = QHBoxLayout()
        self.back = QPushButton("Back")
        self.back.clicked.connect(lambda: self.go(-1))
        actions.addWidget(self.back)
        actions.addStretch()
        self.next = QPushButton()
        self.next.setObjectName("primary")
        self.next.clicked.connect(lambda: self.go(1))
        actions.addWidget(self.next)
        layout.addLayout(actions)
        self.render_step()

    def render_step(self):
        counter, title, body = LESSONS[self.step]
        self.counter.setText(counter)
        self.title.setText(title)
        self.body.setText(body)
        self.illustration.set_step(self.step)
        self.back.setEnabled(self.step > 0)
        self.next.setText("Start measuring" if self.step == 2 else "Next  →")

    def go(self, direction):
        if direction > 0 and self.step == 2:
            self.accept()
            return
        self.step = max(0, min(2, self.step + direction))
        self.render_step()
