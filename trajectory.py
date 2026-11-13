"""Amortized O(1) samples; independent accumulation of path length."""

from math import hypot

import numpy as np

from distance_calculator import Distances


class Trajectory:
    MAX_SAMPLES = 2_000_000

    def __init__(self):
        self._points = np.zeros((4096, 2), dtype=np.float64)
        self.reset()

    def reset(self):
        self.size = 1
        self._points[0] = (0, 0)
        self.path = 0.0
        self.raw_x = self.raw_y = 0
        self.raw_path = 0.0

    def append(self, x: float, y: float, raw_dx=0, raw_dy=0):
        if self.size >= self.MAX_SAMPLES:
            raise OverflowError("Sample limit reached. Finish shorter measurements.")
        if self.size == len(self._points):
            grown = np.empty((min(len(self._points) * 2, self.MAX_SAMPLES), 2))
            grown[: self.size] = self._points
            self._points = grown
        self._points[self.size] = self._points[self.size - 1] + (x, y)
        self.size += 1
        self.path += hypot(x, y)
        self.raw_x += raw_dx
        self.raw_y += raw_dy
        self.raw_path += hypot(raw_dx, raw_dy)

    @property
    def points(self):
        return self._points[: self.size]

    @property
    def distances(self):
        return Distances(*self._points[self.size - 1], self.path)
