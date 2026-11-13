"""Read-only compatibility identifiers for profiles created before the rename."""

import os

LEGACY_DATA_DIRECTORY = "MouseMeasure"


def legacy_data_override():
    return os.environ.get("MOUSEMEASURE_DATA_DIR")
