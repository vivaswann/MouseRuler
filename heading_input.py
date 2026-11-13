"""Optional serial heading adapter; no fabricated IMU data or hidden fallback.

Wire protocol: UTF-8 JSON lines {"yaw_deg": 12.5}, at >=20 Hz, 115200 baud.
Angles are CCW in the app's Y-up frame, referenced to the start orientation.
Receipt timing is not hardware synchronization; use is experimental.
"""

import json
import time
from math import isfinite, radians

import serial


class SerialHeadingSource:
    def __init__(self, port, max_age=0.15):
        self.serial = serial.Serial(port, 115200, timeout=0)
        self.max_age = max_age
        self.buffer = b""
        self.value = self.received = None
        self.zero = 0.0

    def ingest(self, data, now):
        self.buffer += data
        if len(self.buffer) > 65536:
            raise RuntimeError("IMU serial buffer overflow")
        while b"\n" in self.buffer:
            line, self.buffer = self.buffer.split(b"\n", 1)
            if not line.strip():
                continue
            try:
                value = float(json.loads(line)["yaw_deg"])
                if not isfinite(value):
                    raise ValueError("non-finite heading")
            except (ValueError, KeyError, TypeError, UnicodeError) as exc:
                raise RuntimeError(f"Invalid IMU JSON line: {exc}") from exc
            self.value = radians(value)
            self.received = now

    def poll(self):
        try:
            self.ingest(
                self.serial.read(min(self.serial.in_waiting, 65536)), time.monotonic()
            )
        except serial.SerialException as exc:
            raise RuntimeError(f"IMU disconnected: {exc}") from exc

    def heading(self, timestamp):
        if (
            self.value is None
            or self.received is None
            or abs(timestamp - self.received) > self.max_age
        ):
            raise RuntimeError("IMU heading is missing or stale. Recording stopped.")
        return self.value - self.zero

    def set_zero(self):
        self.heading(time.monotonic())
        self.zero = self.value

    def close(self):
        self.serial.close()
