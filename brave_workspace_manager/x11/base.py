"""Common interface of the window backends."""

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

    def maximize(self, window_id: int) -> bool: ...

    def unmaximize(self, window_id: int) -> bool: ...

    def close_window(self, window_id: int) -> bool: ...

    def active_window(self) -> int | None: ...


class NullBackend:
    """Used when there is no window management support (Wayland, no X11)."""

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

    def maximize(self, window_id: int) -> bool:
        return False

    def unmaximize(self, window_id: int) -> bool:
        return False

    def close_window(self, window_id: int) -> bool:
        return False

    def active_window(self) -> int | None:
        return None
