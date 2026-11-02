"""Selection of the window management backend."""

from __future__ import annotations

from .base import NullBackend, WindowBackend
from .wmctrl_backend import WmctrlBackend

__all__ = ["NullBackend", "WindowBackend", "WmctrlBackend", "create_backend"]


def create_backend() -> WindowBackend:
    """Best available backend: python-xlib (native EWMH), falling back to wmctrl."""
    try:
        from .backend import X11Backend

        candidate = X11Backend()
        if candidate.is_available():
            return candidate
    except Exception:  # pragma: no cover - depends on the environment
        pass
    candidate = WmctrlBackend()
    if candidate.is_available():
        return candidate
    return NullBackend()
