"""Physical units and endpoint geometry. Internal physical unit is millimetres."""

from dataclasses import dataclass
from math import hypot, isfinite

UNITS = {"mm": 1.0, "cm": 10.0, "m": 1000.0, "in": 25.4}


def to_mm(value: float, unit: str) -> float:
    if not isfinite(value):
        raise ValueError("Distance must be finite.")
    return value * UNITS[unit]


def from_mm(value: float, unit: str) -> float:
    return value / UNITS[unit]


@dataclass(frozen=True)
class Distances:
    horizontal: float = 0.0
    vertical: float = 0.0
    path: float = 0.0

    @property
    def direct(self) -> float:
        return hypot(self.horizontal, self.vertical)


def endpoint_distance(start, end) -> float:
    return hypot(end[0] - start[0], end[1] - start[1])
