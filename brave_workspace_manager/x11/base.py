"""Interfaz comun de los backends de ventanas."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from ..models import WindowInfo


@runtime_checkable
class WindowBackend(Protocol):
    name: str

    def is_available(self) -> bool: ...

    def list_windows(self) -> list[WindowInfo]: ...

    def activate(self, window_id: int) -> bool: ...

    def minimize(self, window_id: int) -> bool: ...

    def restore(self, window_id: int) -> bool: ...

    def active_window(self) -> int | None: ...


class NullBackend:
    """Usado cuando no hay soporte de gestion de ventanas (Wayland, sin X11)."""

    name = "none"

    def is_available(self) -> bool:
        return False

    def list_windows(self) -> list[WindowInfo]:
        return []

    def activate(self, window_id: int) -> bool:
        return False

    def minimize(self, window_id: int) -> bool:
        return False

    def restore(self, window_id: int) -> bool:
        return False

    def active_window(self) -> int | None:
        return None
