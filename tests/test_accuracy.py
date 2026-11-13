import pytest

from accuracy_analysis import AccuracyTrial, analyse, closure_drift
from measurement_state import Measurement


@pytest.mark.parametrize("step", [1, 5, 25, 100])
def test_synthetic_speed_packetization(step):
    # Packetization only; this is NOT a physical mouse speed experiment.
    m = Measurement()
    m.start("synthetic", 0.1)
    for _ in range(1000 // step):
        m.feed(step, 0, "synthetic")
    assert m.trajectory.distances.direct == pytest.approx(100)


@pytest.mark.parametrize("surface,scale", [("synthetic A", 0.1), ("synthetic B", 0.12)])
def test_synthetic_surface_scale(surface, scale):
    trial = AccuracyTrial(100, 1000 * scale, surface, "simulated", True)
    result = analyse([trial])
    assert result["simulated"]
    assert result["bias_mm"] == pytest.approx(1000 * scale - 100)


def test_repeatability_bias_and_drift():
    trials = [
        AccuracyTrial(100, v, "synthetic", "simulated", True) for v in (99, 100, 101)
    ]
    result = analyse(trials)
    assert result["bias_mm"] == 0
    assert result["repeatability_sd_mm"] == 1
    assert result["rmse_mm"] == pytest.approx((2 / 3) ** 0.5)
    assert closure_drift(3, 4) == 5


def test_no_mixing_simulated_and_physical():
    with pytest.raises(ValueError):
        analyse(
            [
                AccuracyTrial(100, 100, "a", "slow", True),
                AccuracyTrial(100, 100, "a", "slow", False),
            ]
        )


def test_different_conditions_are_not_called_repeatability():
    result = analyse(
        [
            AccuracyTrial(100, 99, "a", "slow", True),
            AccuracyTrial(100, 101, "b", "fast", True),
        ]
    )
    assert result["repeatability_sd_mm"] is None
    assert result["error_sd_mm"] > 0


def test_heading_parser_and_staleness():
    from heading_input import SerialHeadingSource

    # Parser only; no serial port or IMU is simulated as a real connection.
    source = object.__new__(SerialHeadingSource)
    source.buffer = b""
    source.value = None
    source.received = None
    source.zero = 0
    source.max_age = 0.15
    source.ingest(b'{"yaw_deg": 90}\n', 1)
    assert source.heading(1.1) == pytest.approx(3.141592653589793 / 2)
    with pytest.raises(RuntimeError, match="stale"):
        source.heading(1.3)
    with pytest.raises(RuntimeError, match="Invalid"):
        source.ingest(b"not json\n", 2)
