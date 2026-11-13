import math

import pytest

from coordinate_transform import transform
from distance_calculator import endpoint_distance, from_mm, to_mm
from measurement_state import Measurement, State
from trajectory import Trajectory


def measure(vectors, scale=1.0):
    m = Measurement()
    m.start("mouse", scale)
    for x, y in vectors:
        m.feed(x, y, "mouse")
    m.finish()
    return m.trajectory.distances


@pytest.mark.parametrize(
    "vectors,direct,path,x,y",
    [
        ([(3, 4)], 5, 5, 3, -4),
        ([(10, 0)] * 10, 100, 100, 100, 0),
        ([(3, 4), (3, -4)], 6, 10, 6, 0),
        ([(10, 0), (0, 10), (-10, 0), (0, -10)], 0, 40, 0, 0),
        ([(0, 0)], 0, 0, 0, 0),
        ([(-3, -4)], 5, 5, -3, 4),
        ([(10, 0), (-20, 0), (10, 0)], 0, 40, 0, 0),
    ],
)
def test_geometry(vectors, direct, path, x, y):
    d = measure(vectors)
    assert (d.direct, d.path, d.horizontal, d.vertical) == pytest.approx(
        (direct, path, x, y)
    )


def test_curved_arc():
    points = [
        (100 * math.cos(i * math.pi / 200), 100 * math.sin(i * math.pi / 200))
        for i in range(101)
    ]
    vectors = [(b[0] - a[0], b[1] - a[1]) for a, b in zip(points, points[1:])]
    d = measure(vectors)
    assert d.direct == pytest.approx(math.sqrt(20000))
    assert d.path == pytest.approx(math.pi * 50, rel=2e-5)
    assert d.path > d.direct


def test_circle():
    pts = [
        (math.cos(i * math.tau / 1000), math.sin(i * math.tau / 1000))
        for i in range(1001)
    ]
    d = measure([(b[0] - a[0], b[1] - a[1]) for a, b in zip(pts, pts[1:])])
    assert d.direct < 1e-12
    assert d.path == pytest.approx(math.tau, rel=2e-6)


@pytest.mark.parametrize(
    "unit,value", [("mm", 254), ("cm", 25.4), ("m", 0.254), ("in", 10)]
)
def test_units(unit, value):
    assert to_mm(value, unit) == pytest.approx(254)
    assert from_mm(254, unit) == pytest.approx(value)


def test_endpoint_nonzero_start():
    assert endpoint_distance((100, 200), (103, 204)) == 5


def test_scale():
    d = measure([(30, 40)], 0.1)
    assert d.direct == 5
    assert d.path == 5


def test_transform_yaw():
    assert transform(10, 0, 1, math.pi / 2) == pytest.approx((0, 10))
    assert transform(0, 10, 1, math.pi / 2) == pytest.approx((10, 0))


@pytest.mark.parametrize("scale", [0, -1, float("nan"), float("inf")])
def test_invalid_scale(scale):
    with pytest.raises(ValueError):
        transform(1, 1, scale)


def test_growth_keeps_all_samples():
    t = Trajectory()
    for _ in range(10000):
        t.append(1, 0, 1, 0)
    assert t.size == 10001
    assert t.points[-1, 0] == 10000
    assert t.path == t.raw_path == 10000


def test_limit_is_explicit():
    m = Measurement()
    m.start("mouse")
    m.trajectory.MAX_SAMPLES = 2
    m.feed(1, 0, "mouse")
    m.feed(1, 0, "mouse")
    assert m.state == State.ERROR
    assert "limit" in m.error
