import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture(scope="session")
def app():
    from PySide6.QtWidgets import QApplication

    return QApplication.instance() or QApplication([])


@pytest.fixture
def window(app, tmp_path):
    from main import MainWindow
    from settings import Settings

    w = MainWindow(Settings(tmp_path / "settings.json"), enable_raw=False)
    w.router.last_device = "test-mouse"
    w.show()
    app.processEvents()
    yield w
    w.close()
    app.processEvents()
