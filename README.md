# MouseMeasure

**An ordinary mouse. A different kind of ruler.**

MouseMeasure is a local Windows utility for measuring displacement with an optical
mouse. Take a crooked path between two points and read the straight distance
between them, separately from the path you travelled.

**[Download the Windows application](https://github.com/vivaswann/MouseMeasure/releases/download/v1.2.0/MouseMeasure-Windows-1.2.0.zip)**
— extract the ZIP and open `MouseMeasure.exe`. No Python installation is needed.
See the [release notes and checksums](https://github.com/vivaswann/MouseMeasure/releases/tag/v1.2.0).

![The first-launch measuring guide](docs/guide-1.png)

## Start measuring

1. Open MouseMeasure and follow the illustrated guide.
2. Enter your mouse's hardware DPI, or calibrate against a ruler.
3. Align the centre of the scroll wheel or a fixed body mark with the first edge.
4. Double-left-click, slide to the other edge **without rotating or lifting**, and
   double-left-click again. Use the same mark for both alignments.

The pointer hides and stays inside the graph during recording. **Enter** also
starts/finishes, **Escape** cancels, and **R** resets. The result table shows direct
and travelled lengths in **mm, cm, metres, and inches** together.

The optical sensor is underneath the mouse. A wheel or body mark is an alignment
aid: its offset cancels only when you keep the same mouse orientation. The app
cannot recover rotation or motion lost during lift-off. DPI-based lengths are
estimates; ruler calibration refines their scale. No total accuracy is claimed.

## Features

- Raw Input acquisition, independent of pointer speed and screen edges.
- Live trajectory, endpoint markers, direct line, zoom, pan, and fit.
- Animated first-launch lessons with pause control and a replayable Guide.
- Per-device DPI setup, optional ruler calibration, and honest uncertainty labels.
- Light/dark appearance, local diagnostics and JSON export, optional serial yaw.
- No telemetry, account requirement, or uploads.

## Run from source

Windows 11 x64 and Python 3.13 are the tested development configuration.

```powershell
git clone https://github.com/vivaswann/MouseMeasure.git
cd MouseMeasure
py -3.13 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.venv\Scripts\python.exe bootstrap.py
```

`Launch MouseMeasure.bat` launches a packaged executable when present and otherwise
sets up the source environment. Python 3.11+ may work with compatible wheels;
the Windows checks use Python 3.13.

## Develop and build

```powershell
.venv\Scripts\python.exe -m ruff check .
.venv\Scripts\python.exe -m ruff format --check .
.venv\Scripts\python.exe -m pytest -q
.\build.ps1 -Python .venv\Scripts\python.exe
```

The native cursor test requires an interactive desktop; CI uses
`pytest -m "not desktop"`. The build workflow produces a Windows application
artifact on version tags or manual dispatch. Executables are unsigned and kept
out of Git history.

## Learn more

- [Measuring, calibration, DPI detection and limitations](docs/USAGE.md)
- [Contributing and architecture rules](CONTRIBUTING.md)
- [Validation scope](docs/VALIDATION.md)
- [Changes](CHANGELOG.md) · [Security](SECURITY.md)

## License

MouseMeasure source is [MIT licensed](LICENSE). Qt/PySide6 and other bundled
dependencies retain their own licenses; see [third-party notices](THIRD_PARTY_NOTICES.md).
