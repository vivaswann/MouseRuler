# Development guide

[← Documentation](README.md) · [Contributing guidelines](../CONTRIBUTING.md)

## Run from source

Use Windows 11 x64 and Python 3.13. From PowerShell:

```powershell
git clone https://github.com/vivaswann/MouseRuler.git
cd MouseRuler
py -3.13 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.venv\Scripts\python.exe bootstrap.py
```

Add `--wheel` to open directly in Wheel mode, or `--windowed` for a resizable
window. Without arguments, the app opens its normal measurement screen.

## Check a change

Run these commands from the repository root:

```powershell
.venv\Scripts\python.exe -m ruff check .
.venv\Scripts\python.exe -m ruff format --check .
.venv\Scripts\python.exe -m pytest -q
```

The `desktop` test briefly confines and hides the pointer, then restores it. It
requires an interactive Windows desktop. For a headless runner, use:

```powershell
.venv\Scripts\python.exe -m pytest -q -m "not desktop"
```

## Build the Windows executable

```powershell
.\build.ps1 -Python .venv\Scripts\python.exe
```

The build produces `MouseRuler.exe`. Executables are unsigned. The packaged
software integration check is:

```powershell
.\MouseRuler.exe --self-test --report packaged-test.json
```

That check uses synthetic input and temporary profiles; it does not establish
physical measurement accuracy. See [validation](VALIDATION.md) for the limits.

## Source map

| Area | Main files |
| --- | --- |
| Launch and app interface | `bootstrap.py`, `main.py`, `theme.py` |
| Windows input and cursor capture | `mouse_input.py`, `input_handler.py`, `cursor_capture.py` |
| Optical measurement | `measurement_state.py`, `trajectory.py`, `distance_calculator.py`, `coordinate_transform.py` |
| DPI and ruler calibration | `dpi_detection.py`, `calibration.py` |
| Wheel measurement and setup | `wheel_page.py`, `wheel_measurement.py`, `mouse_identity.py` |
| Animated guides and plots | `onboarding.py`, `wheel_guide.py`, `visualization.py` |
| Settings and optional heading input | `settings.py`, `legacy.py`, `heading_input.py` |
| Verification and distribution | `tests/`, `self_test.py`, `MouseRuler.spec`, `build.ps1`, `.github/workflows/` |

Keep optical and wheel scale calculations independent. Use raw sensor/wheel
input for distance; cursor coordinates are only for interface behavior. Attach
manufacturer sources to model hints and leave unsupported dimensions unknown.
