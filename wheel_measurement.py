"""Wheel-path estimates from raw scroll units and explicit wheel geometry."""

import json
import math
import os
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(frozen=True)
class WheelGeometry:
    # Example geometry enables a quick estimate; it is not detected hardware.
    diameter_mm: float = 24.0
    increments_per_turn: float = 24.0
    assumed: bool = True

    def __post_init__(self):
        for value, upper in (
            (self.diameter_mm, 100),
            (self.increments_per_turn, 10000),
        ):
            if (
                isinstance(value, bool)
                or not math.isfinite(value)
                or not 1 <= value <= upper
            ):
                raise ValueError(
                    "Wheel diameter or increments per turn are outside the supported range"
                )
        if not isinstance(self.assumed, bool):
            raise ValueError("Invalid geometry source")

    @property
    def mm_per_unit(self):
        return math.pi * self.diameter_mm / (120 * self.increments_per_turn)


class WheelMeasurement:
    def __init__(self, path):
        self.path = Path(path)
        self.profiles = {}
        self.device = ""
        self.geometry = WheelGeometry()
        self.active_geometry = self.geometry
        self.active = self.completed = False
        self.travel = self.net = 0
        self.status = "Roll the wheel once to select the mouse, then start."
        self.load()

    def load(self):
        if not self.path.exists():
            return
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            if data.get("version") != 1 or not isinstance(data.get("profiles"), dict):
                raise ValueError("Invalid wheel settings")
            profiles = {}
            for device, values in data["profiles"].items():
                if not isinstance(device, str) or not device:
                    raise ValueError("Invalid wheel device")
                profiles[device] = WheelGeometry(**values)
            self.profiles = profiles
        except (OSError, ValueError, TypeError, AttributeError) as exc:
            self.status = (
                f"Wheel settings could not be loaded: {exc}. Using example geometry."
            )

    def save_geometry(self):
        if self.active:
            raise ValueError("Stop recording before saving wheel settings")
        if not self.device:
            raise ValueError("Roll the wheel once to select the mouse first")
        profiles = dict(self.profiles)
        profiles[self.device] = self.geometry
        data = {"version": 1, "profiles": {k: asdict(v) for k, v in profiles.items()}}
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(
            json.dumps(data, indent=2, allow_nan=False), encoding="utf-8"
        )
        os.replace(temporary, self.path)
        self.profiles = profiles
        self.status = "Wheel settings saved for this mouse. Optical DPI and calibration are unchanged."

    def feed(self, packet):
        if (
            self.active
            and packet.device == self.device
            and (packet.absolute or packet.attributes_changed)
        ):
            self.cancel("Mouse input changed. Partial wheel result discarded.")
            return
        if not packet.wheel_delta or packet.absolute:
            return
        if not self.active:
            if packet.device != self.device:
                self.reset()
                self.device = packet.device
                self.geometry = self.profiles.get(self.device, WheelGeometry())
                self.status = "Mouse selected. Ready to estimate the rolled path."
            return
        if packet.device == self.device:
            self.net += packet.wheel_delta
            self.travel += abs(packet.wheel_delta)

    def start(self):
        if self.active:
            raise ValueError("Wheel recording already started")
        if not self.device:
            raise ValueError("Roll the wheel once to select the mouse first")
        self.reset()
        self.active_geometry = self.geometry
        self.active = True
        self.status = "Recording wheel path… Press Enter to finish or Escape to cancel."

    def finish(self):
        if not self.active:
            return
        self.active = False
        self.completed = bool(self.travel)
        self.status = (
            "Finished · geometry-based estimate. Slipping or free-spin can invalidate it."
            if self.completed
            else "No wheel rotation recorded. No measurement produced."
        )

    def reset(self):
        self.active = self.completed = False
        self.net = self.travel = 0

    def cancel(self, reason="Wheel recording cancelled. No completed result saved."):
        self.reset()
        self.status = reason

    @property
    def distance_mm(self):
        if not (self.active or self.completed):
            return None
        return self.travel * self.active_geometry.mm_per_unit
