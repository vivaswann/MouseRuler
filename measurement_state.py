"""Measurement lifecycle; no dependence on Qt or Windows."""

from enum import Enum

from coordinate_transform import transform
from trajectory import Trajectory


class State(str, Enum):
    IDLE = "IDLE"
    RECORDING = "RECORDING"
    COMPLETED = "COMPLETED"
    ERROR = "ERROR"


class Measurement:
    def __init__(self):
        self.trajectory = Trajectory()
        self.state = State.IDLE
        self.error = ""
        self.device = ""
        self.scale = 1.0
        self.calibrated = False
        self.physical_units = False
        self.scale_source = "counts"
        self.heading_source = None

    def start(self, device: str, scale: float | None = None, source=None):
        if not device:
            raise ValueError("Move your physical mouse first so it can be identified.")
        self.trajectory.reset()
        self.device = device
        self.scale = scale if scale is not None else 1.0
        transform(0, 0, self.scale)  # validate before recording
        self.physical_units = scale is not None
        self.scale_source = (source or "calibration") if scale is not None else "counts"
        self.calibrated = self.scale_source == "calibration"
        self.state = State.RECORDING
        self.error = ""

    def feed(self, dx, dy, device, timestamp=0.0):
        if self.state != State.RECORDING or device != self.device:
            return
        try:
            heading = (
                self.heading_source.heading(timestamp) if self.heading_source else None
            )
            x, y = transform(dx, dy, self.scale, heading)
            if dx or dy:
                self.trajectory.append(x, y, dx, dy)
        except (ValueError, OverflowError, RuntimeError) as exc:
            self.fail(str(exc))

    def finish(self):
        if self.state == State.RECORDING:
            self.state = State.COMPLETED

    def reset(self):
        self.trajectory.reset()
        self.state = State.IDLE
        self.error = ""
        self.device = ""
        self.calibrated = False
        self.physical_units = False
        self.scale_source = "counts"

    def cancel(self):
        if self.state == State.RECORDING:
            self.reset()

    def fail(self, message):
        self.error = message
        self.state = State.ERROR
