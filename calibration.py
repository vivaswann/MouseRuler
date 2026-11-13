"""Repeated ruler traversals, using net sensor counts, never cursor pixels."""

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from math import hypot, isfinite
from statistics import mean, stdev

from distance_calculator import to_mm


@dataclass
class CalibrationProfile:
    device: str
    mm_per_count: float
    trials: list[float]
    created: str

    def __post_init__(self):
        if (
            not self.device
            or not isfinite(self.mm_per_count)
            or self.mm_per_count <= 0
            or not self.trials
            or any(not isfinite(x) or x <= 0 for x in self.trials)
        ):
            raise ValueError("Invalid calibration profile.")
        if not abs(mean(self.trials) - self.mm_per_count) <= self.mm_per_count * 1e-9:
            raise ValueError("Calibration coefficient does not match its trials.")

    @property
    def relative_scale_sem(self):
        if len(self.trials) < 2:
            return None
        return stdev(self.trials) / len(self.trials) ** 0.5 / self.mm_per_count

    def as_dict(self):
        return asdict(self)


class CalibrationSession:
    def __init__(self):
        self.device = ""
        self.coefficients = []

    def add_trial(self, reference, unit, raw_x, raw_y, raw_path, device):
        reference_mm = to_mm(reference, unit)
        counts = hypot(raw_x, raw_y)
        if reference_mm <= 0 or reference_mm > 1_000_000:
            raise ValueError("Reference must be greater than zero and at most 1 km.")
        if not isfinite(counts) or counts < 100:
            raise ValueError(
                "Too little motion. Use a longer ruler traverse (at least 100 counts)."
            )
        if (
            not isfinite(raw_path)
            or raw_path < counts - 1e-7
            or counts / raw_path < 0.97
        ):
            raise ValueError(
                "Calibration must follow a straight ruler without backtracking."
            )
        if not device or (self.device and device != self.device):
            raise ValueError("Use the same mouse for every calibration trial.")
        coefficient = reference_mm / counts
        self.device = device
        self.coefficients.append(coefficient)
        return coefficient

    def profile(self):
        if not self.coefficients:
            raise ValueError("Record and add a ruler trial first.")
        return CalibrationProfile(
            self.device,
            mean(self.coefficients),
            list(self.coefficients),
            datetime.now(timezone.utc).isoformat(),
        )
