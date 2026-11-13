# Reproducible single-file Windows build. Run from this directory.
from pathlib import Path
root = Path(SPECPATH)
a = Analysis([str(root / 'bootstrap.py')], pathex=[str(root)],
    binaries=[], datas=[(str(root / 'assets' / 'MouseMeasure.ico'), 'assets')],
    hiddenimports=[],
    hookspath=[], hooksconfig={}, runtime_hooks=[],
    excludes=['PySide6.QtWebEngineCore', 'PySide6.QtWebEngineWidgets',
              'PySide6.QtWebEngineQuick', 'PySide6.QtQml', 'PySide6.QtQuick',
              'PySide6.QtPdf', 'PySide6.QtPdfWidgets', 'tkinter', 'matplotlib',
              'scipy', 'IPython', 'pytest'], noarchive=False)
# Qt 6.12 uses Windows' system ICU API. A foreign ICU found on a build host's
# PATH (e.g. Poppler's ICU with version-suffixed exports) has an incompatible
# ABI. Do not shadow Windows 11's icuuc.dll with that unrelated library.
a.binaries = [item for item in a.binaries
              if not Path(item[0]).name.lower().startswith(('icuuc', 'icuin', 'icudt'))]
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, a.binaries, a.datas, [], name='MouseMeasure',
    debug=False, bootloader_ignore_signals=False, strip=False, upx=False,
    console=False, disable_windowed_traceback=False,
    icon=str(root / 'assets' / 'MouseMeasure.ico'))
