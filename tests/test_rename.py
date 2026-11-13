from calibration import CalibrationSession
from legacy import LEGACY_DATA_DIRECTORY
from settings import Settings, default_settings_path


def clean_environment(monkeypatch, tmp_path):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    monkeypatch.delenv("MOUSERULER_DATA_DIR", raising=False)
    monkeypatch.delenv("MOUSEMEASURE_DATA_DIR", raising=False)


def test_migrates_dpi_calibration_and_preferences(monkeypatch, tmp_path):
    clean_environment(monkeypatch, tmp_path)
    old_path = tmp_path / LEGACY_DATA_DIRECTORY / "settings.json"
    old = Settings(old_path)
    old.dpi_profiles["mouse"] = {"dpi": 1600, "source": "manual"}
    trial = CalibrationSession()
    trial.add_trial(100, "mm", 1000, 0, 1000, "mouse")
    old.profiles["mouse"] = trial.profile()
    old.theme = "Dark"
    old.save()
    original = old_path.read_bytes()
    migrated = Settings()
    assert migrated.path == tmp_path / "MouseRuler" / "settings.json"
    assert migrated.path.exists()
    assert migrated.dpi_profiles["mouse"]["dpi"] == 1600
    assert migrated.profiles["mouse"].mm_per_count == 0.1
    assert migrated.theme == "Dark"
    assert old_path.read_bytes() == original


def test_new_profile_takes_precedence(monkeypatch, tmp_path):
    clean_environment(monkeypatch, tmp_path)
    for folder, unit in [(LEGACY_DATA_DIRECTORY, "in"), ("MouseRuler", "mm")]:
        profile = Settings(tmp_path / folder / "settings.json")
        profile.unit = unit
        profile.save()
    assert Settings().unit == "mm"


def test_explicit_path_stays_isolated(monkeypatch, tmp_path):
    clean_environment(monkeypatch, tmp_path)
    old = Settings(tmp_path / LEGACY_DATA_DIRECTORY / "settings.json")
    old.theme = "Dark"
    old.save()
    assert Settings(tmp_path / "isolated.json").theme == "Light"


def test_new_override_wins(monkeypatch, tmp_path):
    clean_environment(monkeypatch, tmp_path)
    monkeypatch.setenv("MOUSEMEASURE_DATA_DIR", str(tmp_path / "old-override"))
    assert default_settings_path().parent == tmp_path / "old-override"
    monkeypatch.setenv("MOUSERULER_DATA_DIR", str(tmp_path / "new-override"))
    assert default_settings_path().parent == tmp_path / "new-override"


def test_visible_brand(window):
    assert window.windowTitle() == "MouseRuler"
    assert window.findChild(type(window.state_label), "brand").text() == "MouseRuler"
