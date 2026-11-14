# Using MouseRuler

For the independent scroll-wheel method, see [Wheel measurement](WHEEL.md).
The instructions below describe optical slide measurement.


A Windows 11 x64 utility that measures mouse-sensor displacement using Windows Raw Input. It draws the reported trajectory and shows **direct endpoint distance separately from travelled path length**.

## Launch and first measurement

Open **MouseRuler.exe**, or **Launch MouseRuler.bat**. The executable needs no Python installation and runs offline. It starts maximized; `MouseRuler.exe --windowed` opens a resizable window. The executable is unsigned.

1. Move the mouse you intend to measure with, then choose **Set mouse DPI**. An unknown mouse also prompts for DPI when you try to start.
2. The app attempts a read-only HID physical-resolution query. If available, it prefills the reported value for confirmation. Otherwise, enter the hardware DPI currently selected in your mouse software/on the mouse. An initial 800 when no value is known is an editable example, **not a detected value or an assumed measurement scale**.
3. After saving DPI, put the physical mouse at your start point and **double-left-click**. Recording begins; the cursor disappears and stays confined to the graph. Setup itself does not start recording, so movements used to operate the DPI dialog are excluded.
4. Move along your desired path without rotating or lifting the mouse. At the physical endpoint, **double-left-click** again. Recording stops and the cursor reappears.
5. Read the direct distance and longer travelled path. Both lengths appear below the graph in **mm, cm, m, and inches simultaneously**, alongside the primary result in your preferred unit.

Do not hold a button down during movement: start and finish are separate double-click gestures. **Enter** starts/finishes, **Escape** cancels and releases the cursor, and **R** resets. Keep MouseRuler in front. Switching to another app releases the cursor and stops the recording with a partial-trace error. Finish/cancel before using other mouse controls. Movement continues contributing raw sensor counts beyond the pointer's confined range.

## DPI estimates and automatic detection

Windows' standard mouse device information exposes sample/polling rate, **not current hardware DPI**. Display scaling, monitor DPI, Windows pointer speed, and polling rate must never be substituted for sensor DPI.

The implemented detector tries Raw Input preparsed HID metadata and, if needed/permitted, a read-only HID handle. It accepts only unambiguous relative X/Y fields with matching physical linear inch/centimetre scales. Missing units, absolute fields, ambiguous axes, unequal X/Y scales, or inaccessible metadata cause a manual-entry fallback. No feature/output reports are written and no mouse settings are changed.

HID-reported resolution may be static and may not track a vendor's current DPI stage. Confirm it matches your actual setting. The app does not infer DPI from a model name or advertise guessed values as detected. Both devices available in development required the manual fallback. Universal detection of proprietary DPI stages is not implemented.

For DPI-based lengths, `mm_per_count = 25.4 / DPI`. Direct distance uses the norm of the **net** displacement; travelled path sums the norm of **each** displacement. At 1600 DPI, 1600 net counts is approximately 25.4 mm. These results are labelled **DPI-based estimate, not ruler calibrated**.

DPI is saved per mouse. Ruler calibration takes priority. Changing/first entering the DPI for a mouse clears its old ruler profile and pending ruler trials so scales from another DPI setting cannot silently be reused. Other devices' profiles remain. Keep hardware DPI unchanged during a session. DPI save failures roll back settings and appear in the UI.

## Optional ruler calibration

Calibration is optional for a DPI estimate, and can improve the conversion coefficient. You may also calibrate directly without knowing DPI.

1. Open **Calibration**. Choose a ruler reference such as 100 mm.
2. Align a visible body mark with the ruler start, double-click, move straight without rotation/lift/backtracking, then double-click at the endpoint. The cursor hides and confines to the calibration recording area during this traverse.
3. Enter the distance actually traversed and choose **Add this trial**. Move back while stopped and repeat, preferably for three trials.
4. Choose **Save calibration & measure**. The ruler scale now overrides the DPI estimate.

Each trial contributes `reference_mm / hypot(net_raw_x, net_raw_y)`; the profile averages these coefficients. Trials need at least 100 net counts and a net/path ratio of at least 0.97. These are software rejection checks, not proof of physical alignment.

Repeated coefficients estimate scale SEM as `sample_std(coefficients) / sqrt(n)`. The displayed scale-only distance component is `direct_distance × relative_scale_SEM`. It excludes ruler error, systematic scale error, surface effects, rotation, sensor anisotropy, lift-off, and missed reports. It is **not total uncertainty, an accuracy guarantee, or a confidence interval**. Zero repeatability SEM does not mean zero physical error. Validate perpendicular motion too; recalibrate when mouse, DPI, surface, or firmware changes.

## Cursor confinement and click behaviour

Native `ClipCursor` confines the pointer to the graph viewport. Balanced `ShowCursor` calls and a blank Qt cursor hide it. Native client/screen coordinates handle display scaling and monitor placement. The cursor is not repeatedly recentered and its position never contributes to length.

Finish, cancel, reset, tracking errors, disconnect, focus loss, window close, and shutdown release confinement and restore visibility. If Windows denies clipping, recording fails visibly and releases acquired resources. Release does not overwrite a newer clipping rectangle owned by another application. Foreground-only recording replaces the previous background-command option so a hidden/confined cursor is not left in another app.

Double-clicks use Windows timing, require a release between presses, and allow configurable raw-count click jitter (40 counts by default). Stationary triple/quad-click bursts issue one command. Actual movement between start/end pairs rearms detection for quick finishes; for near-stationary bursts, pause between gestures. Increase jitter tolerance for high-DPI mice if clicks are rejected.

The first command locks the mouse device; other devices cannot add motion or finish. Reset releases the lock. Move the intended mouse before a keyboard/button start. Reconnecting to a different port may change its identity. Wheel zooms; drag pans after finishing; Fit view restores framing.

## Physical validation and limitations

For a first check, enter the known DPI and measure between ruler marks **100 mm apart**, taking a sideways detour. Keep heading fixed. Compare the direct result with **100 mm / 10 cm / 0.1 m / about 3.937 in**; the path should be longer. Repeat five times, then perform three ruler calibrations and repeat to compare error. Test speeds and surfaces separately. Do not infer accuracy from decimal places.

One mouse reports local translation and cannot observe its own rotation. Curved paths work only with fixed mouse heading. Lift-off, changed DPI, poor-surface motion loss, and firmware filtering cannot be reconstructed from counts. The optical sensor is the physical reference point; a body mark has the same displacement only while orientation remains fixed. A sliding orientation guide is the smallest mouse-only aid. Changing heading may need an external heading reference, separated sensors, or a camera; an IMU does not recover motion lost while lifted.

Raw Input bypasses Windows pointer acceleration and screen edges, but cannot undo firmware smoothing/angle snapping, radio loss, or report coalescing. Path length includes jitter and may miss curvature between reports. Rendering is antialiased; measurement data is not smoothed to improve apparent accuracy. There is a two-million-movement-sample limit; performance was benchmarked at 100,000 samples, not every long-session load or mouse polling rate. No independent physical accuracy, speed/surface study, or real IMU validation was completed.

## Optional experimental IMU

Settings offers serial yaw at 115200 baud, at least 20 Hz, UTF-8 JSON lines such as `{"yaw_deg":12.5}`. Positive yaw is CCW in the app's Y-up frame; rigidly mount/align the sensor. Heading zeroes at measurement start. Malformed, missing, disconnected, or more than 150 ms stale data stops recording with no silent uncompensated fallback. Calibration always requires fixed orientation. Host receipt times are not synchronized hardware timestamps; drift, latency, and mounting offset require physical characterization. `HeadingSource` supports a future synchronized/fused provider.

## Diagnostics, exports, and settings

Diagnostics includes raw counts, packet/sample counts, device, state, DPI profile, scale source/coefficient, cursor-capture state, click thresholds, last event, and errors. Completed JSON measurements include direct/path values in all four units. Partial traces are labelled and cannot export as completed results. Data stays local; there is no telemetry. Diagnostic files contain device identifiers, so review before sharing.

Atomic settings/DPI/calibration: `%LOCALAPPDATA%\MouseRuler\settings.json`. Runtime errors use a rotating `MouseRuler.log`; import-time failures use `startup-error.log`. `MOUSERULER_DATA_DIR` selects an isolated profile. Existing profiles from before the rename migrate automatically when no new profile exists; the original file is never modified. Explicit profile paths remain isolated.

## Source, tests, and rebuilding

Development used Python 3.13.15. Source targets Python 3.11+ where dependency wheels are available:

```powershell
py -3 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.venv\Scripts\python.exe bootstrap.py
.venv\Scripts\python.exe -m pytest -q
.\build.ps1 -Python .venv\Scripts\python.exe
```

The batch launcher installs runtime dependencies into `.venv` if no executable exists. Initial source installation needs Internet access. Unit/UI tests use synthetic input and temporary profiles. Separate native Windows subprocesses verify real Raw Input registration and cursor clipping/hiding/release. These cursor tests require access to the interactive desktop and are denied by some restricted sandboxes; they restore the cursor in `finally` blocks.

Run the executable's hidden software integration test with:

```powershell
MouseRuler.exe --self-test --report packaged-test.json
```

It uses temporary settings, does not display synthetic results or change user profiles, and explicitly says physical accuracy was not tested. See TEST_REPORT.md, DEVELOPMENT_LOG.md, test-results/, and SHA256SUMS.txt. The source includes the requested modules plus dpi_detection.py, cursor_capture.py, heading_input.py, bootstrap.py, and self_test.py. Third-party licenses are included.

## References

- [Microsoft: standard mouse information; sample rate is not DPI](https://learn.microsoft.com/en-us/windows/win32/api/winuser/ns-winuser-rid_device_info_mouse)
- [Microsoft: HID physical/logical values and units](https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/hidpi/ns-hidpi-_hidp_value_caps)
- [Microsoft: cursor hiding and confinement](https://learn.microsoft.com/windows/win32/menurc/about-cursors)
- [Microsoft: raw relative movement](https://learn.microsoft.com/windows/win32/api/winuser/ns-winuser-rawmouse)
- [Microsoft: native WM_INPUT cleanup](https://learn.microsoft.com/en-us/windows/win32/inputdev/wm-input)

The backend preserves legacy mouse messages and Qt's native cleanup, using INPUTSINK and DEVNOTIFY. Cursor confinement is temporary during recording; Windows pointer settings are unchanged.
