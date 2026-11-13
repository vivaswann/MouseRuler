import pytest

from input_handler import DoubleClickDetector, InputRouter
from input_handler import RawPacket as P
from measurement_state import Measurement, State


def click(detector, t, device="mouse", allowed=True):
    result = detector.feed(P(device, buttons=1, timestamp=t), allowed)
    detector.feed(P(device, buttons=2, timestamp=t + 0.01), allowed)
    return result


def test_pair_once_and_burst_rejected():
    d = DoubleClickDetector()
    assert not click(d, 1)
    assert click(d, 1.1)
    assert not click(d, 1.2)
    assert not click(d, 1.3)
    assert not click(d, 2)
    assert click(d, 2.1)


@pytest.mark.parametrize(
    "gap,expected", [(0.1, True), (0.5, True), (0.501, False), (1, False)]
)
def test_timing(gap, expected):
    d = DoubleClickDetector(interval=0.5)
    assert not click(d, 1)
    assert click(d, 1 + gap) is expected


def test_single_click_rejected():
    d = DoubleClickDetector()
    assert not click(d, 1)


def test_release_required():
    d = DoubleClickDetector()
    assert not d.feed(P("mouse", buttons=1, timestamp=1))
    assert not d.feed(P("mouse", buttons=1, timestamp=1.1))


def test_motion_rejects_two_unrelated_clicks():
    d = DoubleClickDetector()
    click(d, 1)
    d.feed(P("mouse", dx=41, timestamp=1.1))
    assert not click(d, 1.2)


def test_device_separation():
    d = DoubleClickDetector()
    assert not click(d, 1, "one")
    assert not click(d, 1.1, "two")


def test_controls_and_background_rejected():
    d = DoubleClickDetector()
    click(d, 1)
    assert not click(d, 1.1, allowed=False)
    assert not click(d, 1.2)


def test_other_buttons_invalidate():
    d = DoubleClickDetector()
    click(d, 1)
    d.feed(P("mouse", buttons=4, timestamp=1.05))
    assert not click(d, 1.1)


def test_router_records_only_between_commands():
    m = Measurement()

    def command(device):
        m.finish() if m.state == State.RECORDING else m.start(device, 0.1)

    router = InputRouter(m, command)

    def send(t, b=0, x=0, y=0):
        router.feed(P("mouse", x, y, b, t))

    send(0, x=100)
    send(1, 1)
    send(1.01, 2)
    send(1.1, 1)
    send(1.11, 2)
    assert m.state == State.RECORDING
    send(1.2, x=30, y=40)
    # Movement on the endpoint click packet is included before finishing.
    send(2, 1, x=30, y=-40)
    send(2.01, 2)
    send(2.1, 1)
    send(2.11, 2)
    send(3, x=500)
    assert m.state == State.COMPLETED
    assert m.trajectory.distances.direct == 6
    assert m.trajectory.distances.path == 10


def test_other_mouse_cannot_move_or_finish_locked_measurement():
    m = Measurement()
    m.start("one", 1)
    commands = []
    r = InputRouter(m, commands.append)
    r.feed(P("two", 10, 20, 1, 1))
    r.feed(P("two", 0, 0, 2, 1.01))
    r.feed(P("two", 0, 0, 1, 1.1))
    assert not commands
    assert m.trajectory.distances.direct == 0


def test_absolute_input_errors_only_selected_device():
    m = Measurement()
    m.start("mouse")
    r = InputRouter(m, lambda _: None)
    r.feed(P("tablet", absolute=True))
    assert m.state == State.RECORDING
    r.feed(P("mouse", absolute=True))
    assert m.state == State.ERROR


def test_attributes_change_stops_recording():
    m = Measurement()
    m.start("mouse")
    r = InputRouter(m, lambda _: None)
    r.feed(P("mouse", attributes_changed=True))
    assert m.state == State.ERROR


def test_cancel_and_reset():
    m = Measurement()
    m.start("mouse")
    m.feed(4, 5, "mouse")
    m.cancel()
    assert m.state == State.IDLE
    assert m.trajectory.size == 1
    m.start("mouse")
    m.finish()
    m.reset()
    assert m.state == State.IDLE


def test_start_requires_device():
    with pytest.raises(ValueError):
        Measurement().start("")


def test_heading_loss_stops_without_fixed_orientation_fallback():
    class Stale:
        def heading(self, t):
            raise RuntimeError("stale")

    m = Measurement()
    m.start("mouse", 1)
    m.heading_source = Stale()
    m.feed(10, 0, "mouse")
    assert m.state == State.ERROR
    assert m.trajectory.distances.direct == 0
