# Validation scope

The version-1.2 development run passed **130 tests**, including the actual Windows
Raw Input registration test and a brief native cursor-confinement/restoration test.
Formatting and unused-import checks are performed with Ruff. Six onboarding tests
cover lesson navigation, first-run preference, animation pause/lifecycle, explanatory
content, measurement isolation, and the recording-state guard.

The GitHub workflow excludes the `desktop` test because hosted runners may not
provide interactive desktop permissions. Run the full suite on an interactive
Windows desktop to include it. A checked-in workflow is not a claim that a remote
CI run has passed; inspect the repository's Actions results.

Geometry, DPI, calibration, click recognition, and serial framing use synthetic
data. Native registration and cursor clipping use real Windows APIs. No independent
ruler-based physical accuracy study, surface/speed study, or real IMU validation
has been completed. Keep mouse orientation fixed and the sensor in contact.
Displayed decimal places do not establish precision or total uncertainty.

The first-launch drawings are illustrations, never live acquisition or fabricated
measurements. A fixed body mark works because its sensor offset cancels between
endpoints only when orientation is unchanged.
