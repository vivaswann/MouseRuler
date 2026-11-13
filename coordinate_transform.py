"""An explicit boundary between local sensor motion and a fixed reference frame.

Yaw is optional, externally measured, counterclockwise in the app's Y-up frame.
A single mouse cannot infer yaw. Supplying no heading means fixed orientation.
"""

from math import cos, isfinite, sin
from typing import Protocol


class HeadingSource(Protocol):
    def heading(self, timestamp: float) -> float:
        """Return radians or raise if heading is missing/stale."""
        ...


def transform(
    dx: float, dy: float, scale: float = 1.0, heading: float | None = None
) -> tuple[float, float]:
    if not all(isfinite(v) for v in (dx, dy, scale)) or scale <= 0:
        raise ValueError("Non-finite movement or invalid scale.")
    x, y = dx * scale, -dy * scale  # Windows sensor Y points down.
    if heading is None:
        return x, y
    if not isfinite(heading):
        raise ValueError("Invalid heading.")
    c, s = cos(heading), sin(heading)
    return c * x - s * y, s * x + c * y
