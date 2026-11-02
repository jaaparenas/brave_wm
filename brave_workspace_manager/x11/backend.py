"""Backend X11/EWMH basado en python-xlib (sin dependencias de sistema)."""

from __future__ import annotations

from ..models import WindowInfo

try:  # pragma: no cover - depende del entorno
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


class X11Backend:
    """Enumera y controla ventanas mediante el protocolo EWMH."""

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
        """Posicion y tamano de la ventana en coordenadas de pantalla."""
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

    # ------------------------------------------------------------- ventanas

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

    def _send_state(self, window_id: int, state_name: str, remove: bool) -> bool:
        try:
            d = self._display()
            root = d.screen().root
            window = self._window(window_id)
            event = protocol.event.ClientMessage(
                window=window,
                client_type=self._atom("_NET_WM_STATE"),
                data=(32, [0 if remove else 1, self._atom(state_name), 0, 1, 0]),
            )
            root.send_event(event, event_mask=X.SubstructureRedirectMask | X.SubstructureNotifyMask)
            d.flush()
            return True
        except Exception:
            return False

    def restore(self, window_id: int) -> bool:
        ok = self._send_state(window_id, "_NET_WM_STATE_HIDDEN", remove=True)
        try:
            window = self._window(window_id)
            if window.get_attributes().map_state == X.IsUnmapped:
                window.map()
            self._display().flush()
        except Exception:
            pass
        return ok

    def activate(self, window_id: int) -> bool:
        self.restore(window_id)
        try:
            d = self._display()
            root = d.screen().root
            window = self._window(window_id)
            event = protocol.event.ClientMessage(
                window=window,
                client_type=self._atom("_NET_ACTIVE_WINDOW"),
                data=(32, [2, X.CurrentTime, 0, 0, 0]),
            )
            root.send_event(event, event_mask=X.SubstructureRedirectMask | X.SubstructureNotifyMask)
            d.flush()
            return True
        except Exception:
            return False

    def minimize(self, window_id: int) -> bool:
        return self._send_state(window_id, "_NET_WM_STATE_HIDDEN", remove=False)

    def close(self) -> None:
        try:
            if self._connection is not None:
                self._connection.close()
        except Exception:
            pass
        self._connection = None
