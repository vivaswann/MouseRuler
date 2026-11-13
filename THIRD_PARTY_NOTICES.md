# Third-party notices

MouseRuler source is MIT licensed. Its executable bundles CPython, Qt/PySide6, NumPy, PyQtGraph, PySerial and associated runtime components. Original license files and distribution metadata are retained in `third_party_licenses/`.

| Distribution | Version | License metadata |
| --- | --- | --- |
| PySide6 | 6.12.0 | LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only |
| PySide6_Essentials | 6.12.0 | LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only |
| PySide6_Addons | 6.12.0 | LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only |
| shiboken6 | 6.12.0 | LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only |
| numpy | 2.5.4 | BSD-3-Clause AND 0BSD AND MIT AND Zlib AND CC0-1.0 |
| pyqtgraph | 0.14.0 | MIT |
| pyserial | 3.5 | BSD |
| colorama | 0.4.6 | See distribution metadata |
| PyInstaller | 6.22.3 | GPLv2-or-later with a special exception which allows to use PyInstaller to build and distribute non-free programs (including commercial ones) |
| packaging | 26.3 | Apache-2.0 OR BSD-2-Clause |

Qt/PySide6 and Shiboken are used under their applicable open-source license terms, including LGPL v3; copyright remains with The Qt Company and contributors. Qt's LGPL permits modification and reverse engineering for debugging modifications to the LGPL components. Application source, exact dependency pins, and the PyInstaller specification are provided so the application can be rebuilt against modified compatible libraries.

Official upstream source and license references:

- [Qt for Python source](https://code.qt.io/cgit/pyside/pyside-setup.git/)
- [Qt source downloads](https://download.qt.io/official_releases/qt/)
- [GNU LGPL v3](https://www.gnu.org/licenses/lgpl-3.0.html) and [GNU GPL v3](https://www.gnu.org/licenses/gpl-3.0.html)
- [CPython](https://github.com/python/cpython)
- [NumPy](https://github.com/numpy/numpy)
- [PyQtGraph](https://github.com/pyqtgraph/pyqtgraph)
- [PySerial](https://github.com/pyserial/pyserial)
- [PyInstaller](https://github.com/pyinstaller/pyinstaller) (GPL with bootloader distribution exception)

The Qt wheels include a commercial license-reference file alongside metadata identifying their open-source licensing; retaining that file is not a claim of a commercial Qt license. The application does not use Qt WebEngine/PDF/QML components.
