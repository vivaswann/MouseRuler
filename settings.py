"""Versioned, atomic JSON persistence; failures are surfaced to the user."""

import json
import os
from pathlib import Path

from calibration import CalibrationProfile
from legacy import LEGACY_DATA_DIRECTORY, legacy_data_override


def default_settings_path():
    override = os.environ.get("MOUSERULER_DATA_DIR") or legacy_data_override()
    return (
        Path(
            override
            or (Path(os.environ.get("LOCALAPPDATA", Path.home())) / "MouseRuler")
        )
        / "settings.json"
    )


class Settings:
    def __init__(self, path=None):
        self.path = Path(path) if path else default_settings_path()
        self.unit = "cm"
        self.theme = "Light"
        self.background_clicks = False
        self.click_motion_counts = 40
        self.profiles = {}
        self.dpi_profiles = {}
        self.warning = ""
        self.show_guide = True
        source = self.path
        if (
            path is None
            and not source.exists()
            and not (os.environ.get("MOUSERULER_DATA_DIR") or legacy_data_override())
        ):
            previous = (
                Path(os.environ.get("LOCALAPPDATA", Path.home()))
                / LEGACY_DATA_DIRECTORY
                / "settings.json"
            )
            if previous.exists():
                source = previous
        self.load(source)
        if source != self.path and not self.warning:
            try:
                self.save()
            except OSError as exc:
                self.warning = f"Loaded existing settings, but could not save the migrated profile: {exc}"

    def load(self, source=None):
        source = Path(source) if source else self.path
        if not source.exists():
            return
        try:
            obj = json.loads(source.read_text(encoding="utf-8"))
            if obj.get("version") != 1:
                raise ValueError("Unknown settings version")
            if obj.get("unit") not in ("mm", "cm", "m", "in"):
                raise ValueError("Unknown unit")
            if obj.get("theme") not in ("Light", "Dark"):
                raise ValueError("Unknown theme")
            profiles = {
                p.device: p
                for p in (CalibrationProfile(**v) for v in obj.get("profiles", []))
            }
            tolerance = obj.get("click_motion_counts", 40)
            if not isinstance(tolerance, int) or not 4 <= tolerance <= 2000:
                raise ValueError("Invalid double-click motion tolerance")
            self.click_motion_counts = tolerance
            self.show_guide = obj.get("show_guide", True)
            if not isinstance(self.show_guide, bool):
                raise ValueError("Invalid guide preference")
            dpi_profiles = obj.get("dpi_profiles", {})
            from dpi_detection import dpi_scale

            if not isinstance(dpi_profiles, dict):
                raise ValueError("Invalid DPI profiles")
            for device, profile in dpi_profiles.items():
                if (
                    not isinstance(device, str)
                    or not device
                    or not isinstance(profile, dict)
                ):
                    raise ValueError("Invalid DPI device")
                dpi_scale(profile["dpi"])
                if profile.get("source") not in ("manual", "HID reported (confirmed)"):
                    raise ValueError("Invalid DPI source")
            self.dpi_profiles = dpi_profiles
            self.unit, self.theme, self.profiles = obj["unit"], obj["theme"], profiles
            # Background command permission deliberately resets on each launch.
        except (ValueError, TypeError, KeyError, OSError, AttributeError) as exc:
            self.warning = f"Settings could not be loaded: {exc}. Calibrate again."

    def save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        data = dict(
            version=1,
            unit=self.unit,
            theme=self.theme,
            show_guide=self.show_guide,
            click_motion_counts=self.click_motion_counts,
            profiles=[p.as_dict() for p in self.profiles.values()],
            dpi_profiles=self.dpi_profiles,
        )
        tmp.write_text(json.dumps(data, indent=2, allow_nan=False), encoding="utf-8")
        os.replace(tmp, self.path)
