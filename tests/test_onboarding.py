from onboarding import LESSONS, WelcomeGuide
from settings import Settings


def test_new_and_existing_profiles_show_guide(tmp_path):
    settings = Settings(tmp_path / "settings.json")
    assert settings.show_guide
    settings.show_guide = False
    settings.save()
    assert not Settings(settings.path).show_guide


def test_lesson_navigation_and_finish(window):
    guide = WelcomeGuide(window.settings, window)
    assert guide.step == 0 and not guide.back.isEnabled()
    guide.go(1)
    assert guide.step == 1 and guide.back.isEnabled()
    guide.go(-1)
    assert guide.step == 0
    guide.go(1)
    guide.go(1)
    assert guide.next.text() == "Start measuring"
    guide.go(1)
    assert guide.result() == guide.DialogCode.Accepted


def test_guide_does_not_change_measurement(window):
    guide = WelcomeGuide(window.settings, window)
    for step in range(3):
        guide.illustration.set_step(step)
    assert window.measurement.trajectory.size == 1
    assert window.direct_value.text() == "—"


def test_paused_animation_stops_and_hidden_dialog_stops_timer(window, app):
    guide = WelcomeGuide(window.settings, window)
    guide.show()
    app.processEvents()
    guide.illustration.set_paused(True)
    assert not guide.illustration.timer.isActive()
    guide.illustration.set_paused(False)
    assert guide.illustration.timer.isActive()
    guide.close()
    assert not guide.illustration.timer.isActive()


def test_body_mark_offset_limit_is_explained():
    text = " ".join(body for _, _, body in LESSONS)
    assert "offset cancels" in text and "does not rotate" in text


def test_guide_cannot_open_during_recording(window, monkeypatch):
    window.command_button()
    window.show_guide()
    assert "Finish or cancel" in window.message.text()
