"""Illustrative wheel contact and rolling lessons, never synthetic measurements."""

from math import cos, pi, sin

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen

from onboarding import MeasurementIllustration

WHEEL_LESSONS = (
    (
        "01 / POSITION",
        "Let the wheel touch the starting edge.",
        "Hold the mouse so the exposed scroll wheel can roll against the surface and the casing stays clear. Align the wheel’s contact point with your start mark. Turn off free-spin and automatic mode switching.",
    ),
    (
        "02 / ROLL",
        "Start. Roll gently. Stop at the end.",
        "Press Enter to start. Roll steadily with light, consistent pressure. At the end mark, stop the wheel and press Enter again. The length follows the rolled path; backtracking adds length. Escape cancels.",
    ),
    (
        "03 / TRUST THE SCALE",
        "Good contact. A matching wheel setup.",
        "Avoid slipping, sideways dragging, or spinning the wheel in the air. Mouse DPI is not used. Saved wheel settings load automatically. Example dimensions give only a rough estimate; expand Wheel setup to improve them without ruler calibration.",
    ),
)


class WheelIllustration(MeasurementIllustration):
    def __init__(self, dark=False, parent=None):
        super().__init__(dark, parent)
        self.setAccessibleName("Animated wheel measuring instructions")
        self.setAccessibleDescription(
            "Hold the mouse with the wheel touching the surface, roll without slipping, and use Enter to start and stop."
        )

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.scale(self.width() / 800, self.height() / 300)
        ink = QColor("#dbe8dd" if self.dark else "#315441")
        muted = QColor("#a6b3ac" if self.dark else "#6f8275")
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor("#202d28" if self.dark else "#edf2eb"))
        p.drawRoundedRect(QRectF(0, 0, 800, 300), 18, 18)
        p.setFont(QFont("Segoe UI", 11))
        elapsed = self.pause_elapsed if self.paused else self.clock.elapsed()
        phase = min((elapsed % 6500) / 5000, 1)
        if self.step == 2:
            for x, title, caption, lift in (
                (140, "DO · ROLL", "Steady contact", False),
                (400, "DON’T · SLIDE", "Skidding loses distance", False),
                (660, "DON’T · FREE-SPIN", "Air rotation adds distance", True),
            ):
                color = "#315e49" if x == 140 else "#b45e55"
                self.draw_wheel(p, x, 150 if lift else 185, phase * 2 * pi, color)
                p.setPen(QPen(muted, 2))
                p.drawLine(QPointF(x - 90, 203), QPointF(x + 90, 203))
                p.setPen(ink)
                p.drawText(
                    QRectF(x - 125, 223, 250, 24), Qt.AlignmentFlag.AlignCenter, title
                )
                p.setPen(muted)
                p.drawText(
                    QRectF(x - 125, 253, 250, 24), Qt.AlignmentFlag.AlignCenter, caption
                )
            return
        start, end = 140, 660
        x = start + (end - start) * phase if self.step else start
        y = 185
        p.setPen(QPen(muted, 2))
        p.drawLine(QPointF(70, y + 18), QPointF(730, y + 18))
        p.setPen(QPen(muted, 1, Qt.PenStyle.DashLine))
        for mark in (start, end):
            p.drawLine(QPointF(mark, 65), QPointF(mark, 220))
        body = QPainterPath(QPointF(x - 120, y - 12))
        body.cubicTo(x - 125, y - 95, x - 20, y - 90, x + 13, y - 12)
        body.lineTo(x - 120, y - 12)
        p.setPen(QPen(ink, 2))
        p.setBrush(QColor("#34443a" if self.dark else "#d9e3d5"))
        p.drawPath(body)
        self.draw_wheel(
            p, x, y, (x - start) / 18, "#78a466" if self.dark else "#315e49"
        )
        p.setPen(QPen(QColor("#668fa9"), 3))
        p.drawLine(QPointF(start, y + 18), QPointF(x, y + 18))
        p.setPen(ink)
        p.drawText(
            QRectF(170, 28, 500, 28),
            Qt.AlignmentFlag.AlignCenter,
            "SIDE VIEW · WHEEL CONTACTS THE SURFACE",
        )
        p.drawText(QRectF(70, 245, 160, 25), Qt.AlignmentFlag.AlignCenter, "START MARK")
        p.drawText(QRectF(580, 245, 160, 25), Qt.AlignmentFlag.AlignCenter, "END MARK")
        p.setPen(muted)
        p.drawText(
            QRectF(235, 245, 330, 25),
            Qt.AlignmentFlag.AlignCenter,
            "Enter → roll → Enter" if self.step else "Keep the casing clear",
        )

    @staticmethod
    def draw_wheel(p, x, y, angle, color):
        p.setPen(QPen(QColor(color), 3))
        p.setBrush(QColor("#e1ebe1"))
        p.drawEllipse(QPointF(x, y), 18, 18)
        for i in range(6):
            a = angle + i * pi / 3
            p.drawLine(QPointF(x, y), QPointF(x + 14 * cos(a), y + 14 * sin(a)))
