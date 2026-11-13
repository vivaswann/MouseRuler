"""Balanced Win32 cursor hiding and clipping, independent of raw sensor motion."""

import ctypes as C
import os

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication


class RECT(C.Structure):
    _fields_ = [
        ("left", C.c_int32),
        ("top", C.c_int32),
        ("right", C.c_int32),
        ("bottom", C.c_int32),
    ]


class POINT(C.Structure):
    _fields_ = [("x", C.c_int32), ("y", C.c_int32)]


class CursorCapture:
    def __init__(self, api=None):
        self.api = api
        if api is None and os.name == "nt":
            self.api = C.WinDLL("user32", use_last_error=True)
            self.api.ClipCursor.argtypes = [C.POINTER(RECT)]
            self.api.ClipCursor.restype = C.c_int
            self.api.GetClipCursor.argtypes = [C.POINTER(RECT)]
            self.api.GetClipCursor.restype = C.c_int
            self.api.GetClientRect.argtypes = [C.c_void_p, C.POINTER(RECT)]
            self.api.GetClientRect.restype = C.c_int
            self.api.ClientToScreen.argtypes = [C.c_void_p, C.POINTER(POINT)]
            self.api.ClientToScreen.restype = C.c_int
            self.api.ShowCursor.argtypes = [C.c_int]
            self.api.ShowCursor.restype = C.c_int
        self.active = False
        self.hide_calls = 0
        self.override = False
        self.widget = None
        self.bounds = None
        self.requested_bounds = None
        self.previous = None

    @staticmethod
    def values(rect):
        return (rect.left, rect.top, rect.right, rect.bottom)

    def rectangle(self, widget):
        # Win32 native client/screen coordinates avoid Qt logical-vs-physical
        # pixel errors on scaled and multi-monitor desktops.
        hwnd = int(widget.winId())
        rect = RECT()
        origin = POINT(0, 0)
        if not self.api.GetClientRect(
            hwnd, C.byref(rect)
        ) or not self.api.ClientToScreen(hwnd, C.byref(origin)):
            raise RuntimeError("Cannot locate the graph's native screen rectangle.")
        width, height = rect.right - rect.left, rect.bottom - rect.top
        if width < 2 or height < 2:
            raise RuntimeError("The graph must be visible before recording.")
        return RECT(origin.x, origin.y, origin.x + width, origin.y + height)

    def acquire(self, widget):
        if self.active:
            return
        if not self.api:
            raise RuntimeError("Cursor confinement requires Windows.")
        previous = RECT()
        if not self.api.GetClipCursor(C.byref(previous)):
            raise RuntimeError("Cannot read the current cursor confinement.")
        self.previous = previous
        self.widget = widget
        self.bounds = self.rectangle(widget)
        self.requested_bounds = self.bounds
        if not self.api.ClipCursor(C.byref(self.bounds)):
            self.widget = None
            raise RuntimeError(
                f"Windows could not confine the cursor to the graph (error {C.get_last_error()})."
            )
        self.active = True
        try:
            observed = RECT()
            if self.api.GetClipCursor(C.byref(observed)):
                self.bounds = observed
            # A blank Qt cursor also prevents WM_SETCURSOR from repainting an
            # arrow while the Win32 visibility counter is hidden.
            QApplication.setOverrideCursor(Qt.CursorShape.BlankCursor)
            self.override = True
            for _ in range(16):
                count = self.api.ShowCursor(False)
                self.hide_calls += 1
                if count < 0:
                    break
            else:
                raise RuntimeError("Windows could not hide the cursor.")
        except Exception:
            self.release()
            raise

    def update(self):
        if not self.active:
            return
        rect = self.rectangle(self.widget)
        if self.values(rect) != self.values(self.requested_bounds):
            if not self.api.ClipCursor(C.byref(rect)):
                raise RuntimeError("Cannot update the graph cursor boundary.")
            self.bounds = rect
            self.requested_bounds = rect
            observed = RECT()
            if self.api.GetClipCursor(C.byref(observed)):
                self.bounds = observed

    def release(self, restore_previous=True):
        if self.active:
            current = RECT()
            # Do not overwrite a newer confinement set by another application.
            if self.api.GetClipCursor(C.byref(current)) and self.values(
                current
            ) == self.values(self.bounds):
                target = (
                    C.byref(self.previous)
                    if restore_previous and self.previous is not None
                    else None
                )
                if not self.api.ClipCursor(target):
                    self.api.ClipCursor(None)
            self.active = False
        while self.hide_calls:
            self.api.ShowCursor(True)
            self.hide_calls -= 1
        if self.override:
            QApplication.restoreOverrideCursor()
            self.override = False
        self.widget = None
