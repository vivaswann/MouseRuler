"""Log import-time startup failures too, including in a windowless executable."""

import ctypes
import json
import os
import sys
import traceback
from pathlib import Path


def launch():
    try:
        from main import main

        return main()
    except Exception:
        detail = traceback.format_exc()
        directory = Path(
            os.environ.get("MOUSEMEASURE_DATA_DIR")
            or (Path(os.environ.get("LOCALAPPDATA", Path.home())) / "MouseMeasure")
        )
        log_path = directory / "startup-error.log"
        try:
            directory.mkdir(parents=True, exist_ok=True)
            log_path.write_text(detail, encoding="utf-8")
        except OSError:
            pass
        if "--self-test" in sys.argv:
            try:
                report = Path(sys.argv[sys.argv.index("--report") + 1])
                report.parent.mkdir(parents=True, exist_ok=True)
                report.write_text(
                    json.dumps(
                        {
                            "status": "failed",
                            "phase": "startup",
                            "physical_accuracy_tested": False,
                            "error": detail,
                        },
                        indent=2,
                    ),
                    encoding="utf-8",
                )
            except (ValueError, IndexError, OSError):
                pass
        elif os.name == "nt":
            ctypes.windll.user32.MessageBoxW(
                None,
                f"MouseMeasure could not start.\n\n{detail}\nDetails: {log_path}",
                "MouseMeasure startup error",
                0x10,
            )
        if sys.stderr:
            sys.stderr.write(detail)
        return 1


if __name__ == "__main__":
    sys.exit(launch())
