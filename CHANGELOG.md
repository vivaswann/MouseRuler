# Changelog

## 1.4.1

- Scope wheel input filtering to the visible page and detach it during shutdown.
- Explicitly delete test widgets before QApplication teardown to keep hosted Windows checks stable.


## 1.4.0

- Added independent wheel-path measurement with four-unit results and keyboard controls.
- Added animated wheel lessons, a compact setup panel, automatic settings saving, and a one-turn step counter.
- Read-only HID mouse names and manufacturer-sourced partial model hints; receiver identities and unknown wheel diameters remain explicitly unresolved.
- Preserved optical measurement, DPI setup, ruler calibration, and existing saved settings.


## 1.3.0

- Renamed the app, repository, builds, exports, documentation, and releases to MouseRuler.
- Automatically migrate existing DPI and ruler-calibration profiles to the new data folder.
- Preserve support for the original profile-directory environment variable.

## 1.2.0

- Animated first-launch lessons for wheel/body-mark alignment, fixed-heading
  movement, and avoiding rotation or lift-off; pause, replay, and startup preference.
- Refined measurement heading and shared light/dark appearance for the guide.
- Consistent formatting, import cleanup, and a separate appearance module.
- Contributor guidance, issue/PR templates, Windows CI and executable build workflow.

## 1.1.0

- DPI setup with read-only resolution detection and honest manual fallback.
- Hidden, confined cursor during recording with release on every exit path.
- Direct and travelled length table in all four units.

## 1.0.0

- Windows Raw Input acquisition, independent endpoint/path mathematics, ruler
  calibration, trajectory canvas, diagnostics, units, and optional serial heading.
