"""Deterministic per-device raw click recognizer and command routing."""

from dataclasses import dataclass
from math import hypot


@dataclass(frozen=True)
class RawPacket:
    device: str
    dx: int = 0
    dy: int = 0
    buttons: int = 0
    timestamp: float = 0.0
    absolute: bool = False
    attributes_changed: bool = False


class DoubleClickDetector:
    def __init__(self, interval=0.5, max_motion=40):
        self.interval = interval
        self.max_motion = max_motion
        self.reset()

    def reset(self):
        self.device = None
        self.first = None
        self.down = False
        self.motion = 0.0
        self.last_down = None
        self.burst = False

    def feed(self, packet: RawPacket, allowed=True):
        if packet.device != self.device:
            self.reset()
            self.device = packet.device
        if not allowed or packet.absolute:
            self.reset()
            return False
        self.motion += hypot(packet.dx, packet.dy)
        if self.motion > self.max_motion:
            self.first = None
            # Real motion after a completed click pair separates a new endpoint
            # gesture from stationary triple/quad-click noise, even on short trips.
            self.burst = False
        # Any unrelated button/wheel invalidates a candidate pair.
        if packet.buttons & ~0x0003:
            self.first = None
        fired = False
        if packet.buttons & 0x0001:  # left down; only a released button can click again
            t = packet.timestamp
            previous = self.last_down
            if (
                self.burst
                and previous is not None
                and 0 <= t - previous <= self.interval
            ):
                self.last_down = t
                self.down = True
                return False
            self.burst = False
            if not self.down:
                if self.first is not None and 0 < t - self.first <= self.interval:
                    fired = True
                    self.first = None
                    self.burst = True
                else:
                    self.first = t
                self.motion = 0
            self.last_down = t
            self.down = True
        if packet.buttons & 0x0002:
            self.down = False
        return fired


class InputRouter:
    def __init__(self, measurement, command, interval=0.5):
        self.measurement = measurement
        self.command = command
        self.detector = DoubleClickDetector(interval)
        self.last_device = ""
        self.last_event = "Waiting for a physical mouse"
        self.packets = 0
        self.counts_x = self.counts_y = 0
        self.errors = []

    def error(self, message):
        if not self.errors or self.errors[-1] != message:
            self.errors = (self.errors + [message])[-20:]
        from measurement_state import State

        if self.measurement.state == State.RECORDING:
            self.measurement.fail(message)
        self.last_event = message

    def feed(self, packet: RawPacket, allowed=True):
        self.packets += 1
        if packet.absolute:
            self.last_event = (
                "Ignored absolute input (tablet, remote input, or unsupported mouse)"
            )
            if packet.device == self.measurement.device:
                self.error(
                    "Selected mouse reported absolute coordinates; recording stopped."
                )
            return
        if packet.attributes_changed and packet.device == self.measurement.device:
            self.error("Mouse attributes changed. Recheck DPI and recalibrate.")
            return
        from measurement_state import State

        locked = self.measurement.state in (State.RECORDING, State.COMPLETED)
        if locked and packet.device != self.measurement.device:
            return
        self.last_device = packet.device
        self.counts_x += packet.dx
        self.counts_y += packet.dy
        self.last_event = (
            f"Δ {packet.dx:+d}, {packet.dy:+d} · buttons 0x{packet.buttons:04X}"
        )
        self.measurement.feed(packet.dx, packet.dy, packet.device, packet.timestamp)
        if self.detector.feed(packet, allowed):
            self.command(packet.device)
