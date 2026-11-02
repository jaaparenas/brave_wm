"""Global keyboard shortcuts through a passive grab on the X11 root window."""

from __future__ import annotations

import contextlib
import select
import threading
from collections.abc import Callable

MODIFIER_BITS = {
    "ctrl": "ControlMask",
    "control": "ControlMask",
    "alt": "Mod1Mask",
    "shift": "ShiftMask",
    "super": "Mod4Mask",
    "meta": "Mod4Mask",
    "win": "Mod4Mask",
}

KEY_ALIASES = {
    "tab": "Tab",
    "escape": "Escape",
    "esc": "Escape",
    "space": "space",
    "return": "Return",
    "enter": "Return",
    "left": "Left",
    "right": "Right",
    "up": "Up",
    "down": "Down",
    "home": "Home",
    "end": "End",
    "pageup": "Prior",
    "pagedown": "Next",
}


def parse_sequence(sequence: str) -> tuple[set[str], str]:
    parts = [part.strip().lower() for part in sequence.split("+") if part.strip()]
    if not parts:
        raise ValueError("Secuencia de atajo vacia")
    return set(parts[:-1]), parts[-1]


class ShortcutGrabber:
    """Reserves global key combinations and reports when they are pressed."""

    def __init__(self, on_trigger: Callable[[str], None]) -> None:
        self._on_trigger = on_trigger
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()
        self._ready = threading.Event()
        self._bindings: dict[tuple[int, int], str] = {}
        self._failed: dict[str, str] = {}
        self._display = None

    @property
    def failed(self) -> dict[str, str]:
        return dict(self._failed)

    def start(self, bindings: dict[str, str]) -> dict[str, str]:
        """Starts the grab. Returns the shortcuts that could not be reserved."""
        self.stop()
        self._stop.clear()
        self._ready.clear()
        self._failed = {}
        self._bindings.clear()
        self._thread = threading.Thread(
            target=self._run, args=(dict(bindings),), name="shortcut-grabber", daemon=True
        )
        self._thread.start()
        self._ready.wait(timeout=3.0)
        return dict(self._failed)

    def stop(self) -> None:
        self._stop.set()
        thread = self._thread
        if thread is not None and thread.is_alive():
            thread.join(timeout=1.5)
        self._thread = None

    # ------------------------------------------------------------- interno

    def _error_handler(self, action: str):
        """Returns a handler that records the shortcut X11 refused."""

        def handler(error, request=None) -> None:  # pragma: no cover - X11 error path
            name = type(error).__name__
            if name == "BadAccess":
                self._failed[action] = "El servidor X ya tiene esa combinacion reservada"
            else:
                self._failed[action] = f"X11 refused the shortcut ({name})"

        return handler

    def _resolve_keycode(self, display, key: str) -> int:
        from Xlib import XK

        name = KEY_ALIASES.get(key, key)
        keysym = XK.string_to_keysym(name) if len(name) > 1 else 0
        if not keysym and len(key) == 1:
            keysym = ord(key)
        if not keysym:
            raise ValueError(f"Tecla no reconocida: {key}")
        return display.keysym_to_keycode(keysym)

    def _run(self, bindings: dict[str, str]) -> None:
        try:
            from Xlib import X
            from Xlib import display as xdisplay
        except Exception:  # pragma: no cover
            self._ready.set()
            return
        try:
            connection = xdisplay.Display()
        except Exception:  # pragma: no cover
            self._ready.set()
            return
        self._display = connection
        root = connection.screen().root
        for action, sequence in bindings.items():
            try:
                modifiers, key = parse_sequence(sequence)
                mask = 0
                for modifier in modifiers:
                    bit = MODIFIER_BITS.get(modifier)
                    if bit is None:
                        raise ValueError(f"Modificador desconocido: {modifier}")
                    mask |= getattr(X, bit)
                keycode = self._resolve_keycode(connection, key)
                root.grab_key(
                    keycode,
                    mask,
                    False,
                    X.GrabModeAsync,
                    X.GrabModeAsync,
                    onerror=self._error_handler(action),
                )
                self._bindings[(keycode, mask)] = action
            except Exception as exc:
                self._failed[action] = str(exc)
        try:
            root.change_attributes(event_mask=X.KeyPressMask)
            connection.sync()
        except Exception:
            pass
        self._ready.set()

        while not self._stop.is_set():
            try:
                pending = connection.pending_events()
                if not pending:
                    readable, _, _ = select.select([connection.fileno()], [], [], 0.2)
                    if not readable:
                        continue
                    pending = 1
                for _ in range(pending):
                    event = connection.next_event()
                    if event.type == X.KeyPress:
                        action = self._match(event.detail, event.state)
                        if action:
                            with contextlib.suppress(Exception):
                                self._on_trigger(action)
            except Exception:
                break
        with contextlib.suppress(Exception):
            connection.close()
        self._display = None

    def _match(self, keycode: int, state: int) -> str | None:
        from Xlib import X

        relevant = (
            X.ControlMask
            | X.Mod1Mask
            | X.Mod2Mask
            | X.Mod3Mask
            | X.Mod4Mask
            | X.Mod5Mask
            | X.ShiftMask
        )
        pressed = state & relevant
        best_action = None
        best_score = -1
        for (bound_keycode, mask), action in self._bindings.items():
            if bound_keycode != keycode:
                continue
            if (pressed & mask) != mask:
                continue
            score = bin(mask).count("1")
            if score > best_score:
                best_score = score
                best_action = action
        return best_action
