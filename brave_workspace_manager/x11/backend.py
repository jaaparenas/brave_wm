"""X11/EWMH backend built on python-xlib (no system dependency)."""

from __future__ import annotations

from ..models import WindowInfo

try:  # pragma: no cover - depends on the environment
    from Xlib import X, Xatom, display, error, protocol
except Exception:  # pragma: no cover
    X = Xatom = display = error = protocol = None  # type: ignore[assignment]

ATOMS = (
    "_NET_CLIENT_LIST",
    "_NET_ACTIVE_WINDOW",
    "_NET_WM_NAME",
    "_NET_WM_PID",
    "_NET_WM_STATE",
    "_NET_WM_STATE_HIDDEN",
    "_NET_WM_STATE_MINIMIZED",
    "_NET_WM_STATE_MAXIMIZED_VERT",
    "_NET_WM_STATE_MAXIMIZED_HORZ",
)


ICONIC_STATE = 3  # ICCCM IconicState, for WM_CHANGE_STATE


class X11Backend:
    """Lists and controls windows through the EWMH protocol."""

    name = "x11"

    def __init__(self) -> None:
        self._connection = None
        self._atoms: dict[str, int] = {}

    # ------------------------------------------------------------- utilidades

    def _display(self):
        if self._connection is None:
            self._connection = display.Display()
        return self._connection

    def _atom(self, name: str) -> int:
        if name not in self._atoms:
            self._atoms[name] = self._display().intern_atom(name)
        return self._atoms[name]

    def is_available(self) -> bool:
        if display is None:
            return False
        try:
            self._display()
        except Exception:
            return False
        return True

    def _window(self, window_id: int):
        return self._display().create_resource_object("window", window_id)

    def _property(self, window, name: str):
        try:
            return window.get_full_property(self._atom(name), X.AnyPropertyType)
        except Exception:
            return None

    @staticmethod
    def _as_text(value) -> str:
        if value is None:
            return ""
        if isinstance(value, bytes):
            return value.decode("utf-8", "replace")
        if isinstance(value, (list, tuple)):
            chunks = []
            for item in value:
                if isinstance(item, bytes):
                    chunks.append(item)
                elif isinstance(item, str):
                    chunks.append(item.encode("utf-8"))
                else:
                    chunks.append(str(item).encode("utf-8"))
            return b"\0".join(chunks).decode("utf-8", "replace")
        return str(value)

    def _text_property(self, window, name: str) -> str:
        prop = self._property(window, name)
        if prop is None:
            return ""
        return self._as_text(prop.value)

    def _int_property(self, window, name: str) -> int:
        prop = self._property(window, name)
        if prop is None:
            return 0
        value = prop.value
        if value is None:
            return 0
        if isinstance(value, int):
            return value
        try:
            first = value[0]
        except (TypeError, IndexError, KeyError):
            return 0
        try:
            return int(first)
        except (TypeError, ValueError):
            return 0

    def _state_names(self, window) -> set[str]:
        prop = self._property(window, "_NET_WM_STATE")
        if prop is None or not prop.value:
            return set()
        names: set[str] = set()
        for atom in prop.value:
            try:
                names.add(self._display().get_atom_name(int(atom)))
            except Exception:
                continue
        return names

    def _geometry(self, window) -> tuple[int, int, int, int]:
        """Position and size of the window in screen coordinates."""
        try:
            geo = window.get_geometry()
            x, y = geo.x, geo.y
            width, height = geo.width, geo.height
        except Exception:
            return (0, 0, 0, 0)
        try:
            root = self._display().screen().root
            coords = root.translate_coords(window, 0, 0)
            x, y = coords.x, coords.y
        except Exception:
            pass
        return (int(x), int(y), int(width), int(height))

    # ------------------------------------------------------------- windows

    def list_windows(self) -> list[WindowInfo]:
        try:
            d = self._display()
            root = d.screen().root
            prop = root.get_full_property(self._atom("_NET_CLIENT_LIST"), X.AnyPropertyType)
        except Exception:
            return []
        if prop is None or not prop.value:
            return []
        active = self.active_window()
        windows: list[WindowInfo] = []
        for raw_id in prop.value:
            window_id = int(raw_id)
            try:
                window = self._window(window_id)
                title = self._text_property(window, "_NET_WM_NAME")
                if not title:
                    title = self._text_property(window, "WM_NAME")
                wm_class = self._text_property(window, "WM_CLASS").replace("\0", " ")
                pid = self._int_property(window, "_NET_WM_PID")
                states = self._state_names(window)
                geometry = self._geometry(window)
            except Exception:
                continue
            windows.append(
                WindowInfo(
                    window_id=window_id,
                    pid=pid,
                    title=title.strip(),
                    wm_class=wm_class.strip(),
                    is_active=window_id == active,
                    is_minimized=(
                        "_NET_WM_STATE_HIDDEN" in states or "_NET_WM_STATE_MINIMIZED" in states
                    ),
                    is_maximized=(
                        "_NET_WM_STATE_MAXIMIZED_VERT" in states
                        or "_NET_WM_STATE_MAXIMIZED_HORZ" in states
                    ),
                    x=geometry[0],
                    y=geometry[1],
                    width=geometry[2],
                    height=geometry[3],
                )
            )
        return windows

    def active_window(self) -> int | None:
        try:
            d = self._display()
            root = d.screen().root
            prop = root.get_full_property(self._atom("_NET_ACTIVE_WINDOW"), X.AnyPropertyType)
        except Exception:
            return None
        if prop is None or not prop.value:
            return None
        try:
            return int(prop.value[0])
        except (TypeError, ValueError):
            return None

    # ------------------------------------------------------------- acciones

    def _send_root_message(self, window_id: int, message: str, data: list[int]) -> bool:
        """Sends a client message to the window manager about a window."""
        try:
            d = self._display()
            root = d.screen().root
            window = self._window(window_id)
            event = protocol.event.ClientMessage(
                window=window,
                client_type=self._atom(message),
                data=(32, [*data, 0, 0, 0, 0, 0][:5]),
            )
            root.send_event(event, event_mask=X.SubstructureRedirectMask | X.SubstructureNotifyMask)
            d.flush()
            return True
        except Exception:
            return False

    def _send_state(self, window_id: int, states: tuple[str, ...], remove: bool) -> bool:
        """Adds or removes up to two EWMH states in a single request."""
        atoms = [self._atom(name) for name in states] + [0]
        return self._send_root_message(
            window_id, "_NET_WM_STATE", [0 if remove else 1, atoms[0], atoms[1], 1]
        )

    def restore(self, window_id: int) -> bool:
        """Brings a minimised window back.

        Only the window manager may clear ``_NET_WM_STATE_HIDDEN``; the
        standard way to de-iconify is to map the window and request
        ``_NET_ACTIVE_WINDOW``.
        """
        try:
            window = self._window(window_id)
            if window.get_attributes().map_state == X.IsUnmapped:
                window.map()
            self._display().flush()
        except Exception:
            pass
        return self._send_root_message(window_id, "_NET_ACTIVE_WINDOW", [2, X.CurrentTime])

    def activate(self, window_id: int) -> bool:
        return self.restore(window_id)

    def minimize(self, window_id: int) -> bool:
        """Iconifies the window the ICCCM way (WM_CHANGE_STATE, IconicState).

        Window managers such as Muffin ignore requests to add
        ``_NET_WM_STATE_HIDDEN``, because that state belongs to them.
        """
        return self._send_root_message(window_id, "WM_CHANGE_STATE", [ICONIC_STATE])

    def maximize(self, window_id: int) -> bool:
        """Maximises the window and brings it to the front so the change is visible."""
        ok = self._send_state(
            window_id, ("_NET_WM_STATE_MAXIMIZED_VERT", "_NET_WM_STATE_MAXIMIZED_HORZ"), False
        )
        self.restore(window_id)
        return ok

    def unmaximize(self, window_id: int) -> bool:
        """Restores the previous size and brings the window to the front."""
        ok = self._send_state(
            window_id, ("_NET_WM_STATE_MAXIMIZED_VERT", "_NET_WM_STATE_MAXIMIZED_HORZ"), True
        )
        self.restore(window_id)
        return ok

    def close_window(self, window_id: int) -> bool:
        """Asks the window to close the polite way (WM_DELETE_WINDOW)."""
        try:
            d = self._display()
            window = self._window(window_id)
            event = protocol.event.ClientMessage(
                window=window,
                client_type=self._atom("WM_PROTOCOLS"),
                data=(32, [self._atom("WM_DELETE_WINDOW"), X.CurrentTime, 0, 0, 0]),
            )
            window.send_event(event, event_mask=X.NoEventMask)
            d.flush()
            return True
        except Exception:
            return False

    def close(self) -> None:
        try:
            if self._connection is not None:
                self._connection.close()
        except Exception:
            pass
        self._connection = None
