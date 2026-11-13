import pytest

from calibration import CalibrationProfile, CalibrationSession
from settings import Settings


def test_known_distance():
    c = CalibrationSession()
    assert c.add_trial(10, "cm", 2000, 0, 2000, "mouse") == 0.05
    assert c.profile().relative_scale_sem is None


def test_repeated_trials():
    c = CalibrationSession()
    for x in (1000, 1005, 995):
        c.add_trial(100, "mm", x, 0, x, "mouse")
    assert len(c.profile().trials) == 3
    assert c.profile().relative_scale_sem > 0


@pytest.mark.parametrize(
    "value,unit", [(100, "mm"), (10, "cm"), (0.1, "m"), (100 / 25.4, "in")]
)
def test_calibration_units(value, unit):
    c = CalibrationSession()
    c.add_trial(value, unit, 1000, 0, 1000, "mouse")
    assert c.profile().mm_per_count == pytest.approx(0.1)


@pytest.mark.parametrize(
    "reference,counts,path",
    [
        (0, 1000, 1000),
        (-1, 1000, 1000),
        (float("nan"), 1000, 1000),
        (float("inf"), 1000, 1000),
        (100, 0, 0),
        (100, 99, 99),
        (100, 1000, 2000),
        (100, 1000, 999),
        (100, 1000, float("nan")),
    ],
)
def test_invalid_trials(reference, counts, path):
    with pytest.raises(ValueError):
        CalibrationSession().add_trial(reference, "mm", counts, 0, path, "mouse")


def test_mouse_cannot_change_between_trials():
    c = CalibrationSession()
    c.add_trial(100, "mm", 1000, 0, 1000, "one")
    with pytest.raises(ValueError):
        c.add_trial(100, "mm", 1000, 0, 1000, "two")


def test_persistence_and_background_opt_in_resets(tmp_path):
    c = CalibrationSession()
    c.add_trial(100, "mm", 1000, 0, 1000, "mouse")
    s = Settings(tmp_path / "settings.json")
    s.unit = "in"
    s.theme = "Dark"
    s.background_clicks = True
    s.profiles["mouse"] = c.profile()
    s.save()
    reloaded = Settings(s.path)
    assert reloaded.unit == "in"
    assert reloaded.theme == "Dark"
    assert reloaded.profiles["mouse"].mm_per_count == 0.1
    assert not reloaded.background_clicks


def test_corrupt_settings_are_visible(tmp_path):
    p = tmp_path / "settings.json"
    p.write_text("{bad", encoding="utf-8")
    s = Settings(p)
    assert s.warning and not s.profiles


def test_profile_nonfinite_rejected():
    with pytest.raises(ValueError):
        CalibrationProfile("mouse", float("nan"), [1], "today")


def test_empty_session_not_saved():
    with pytest.raises(ValueError):
        CalibrationSession().profile()
