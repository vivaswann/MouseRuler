"""Empirical error statistics. Callers must label simulation versus physical data."""

from dataclasses import dataclass
from math import isfinite, sqrt
from statistics import mean, stdev


@dataclass(frozen=True)
class AccuracyTrial:
    reference_mm: float
    measured_mm: float
    surface: str
    speed: str
    simulated: bool


def analyse(trials: list[AccuracyTrial]):
    if not trials:
        raise ValueError("At least one trial is required.")
    if len({t.simulated for t in trials}) != 1:
        raise ValueError("Do not pool simulated and physical trials.")
    if any(
        not isfinite(t.reference_mm)
        or not isfinite(t.measured_mm)
        or t.reference_mm < 0
        or t.measured_mm < 0
        for t in trials
    ):
        raise ValueError("Distances must be finite and nonnegative.")
    errors = [t.measured_mm - t.reference_mm for t in trials]
    same_conditions = len({(t.reference_mm, t.surface, t.speed) for t in trials}) == 1
    error_sd = stdev(errors) if len(errors) > 1 else None
    return dict(
        n=len(errors),
        simulated=trials[0].simulated,
        bias_mm=mean(errors),
        rmse_mm=sqrt(mean(e * e for e in errors)),
        error_sd_mm=error_sd,
        repeatability_sd_mm=error_sd if same_conditions else None,
        max_abs_error_mm=max(map(abs, errors)),
    )


def closure_drift(x_mm, y_mm):
    if not isfinite(x_mm) or not isfinite(y_mm):
        raise ValueError("Drift coordinates must be finite.")
    return (x_mm * x_mm + y_mm * y_mm) ** 0.5
