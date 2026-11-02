"""Seleccion del backend de gestion de ventanas."""

from __future__ import annotations

from .base import NullBackend, WindowBackend
from .wmctrl_backend import WmctrlBackend

__all__ = ["NullBackend", "WindowBackend", "WmctrlBackend", "create_backend"]


def create_backend() -> WindowBackend:
    """Mejor backend disponible: python-xlib (EWMH nativo) y, si falla, wmctrl."""
    try:
        from .backend import X11Backend

        candidate = X11Backend()
        if candidate.is_available():
            return candidate
    except Exception:  # pragma: no cover - depende del entorno
        pass
    candidate = WmctrlBackend()
    if candidate.is_available():
        return candidate
    return NullBackend()
