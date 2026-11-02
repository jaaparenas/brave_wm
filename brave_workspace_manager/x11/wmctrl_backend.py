"""Alternative backend based on the wmctrl command line tool."""

from __future__ import annotations

import shutil
import subprocess

from ..models import WindowInfo


class WmctrlBackend:
    """Uses wmctrl to list and activate windows (fallback of python-xlib)."""

    name = "wmctrl"

    def __init__(self) -> None:
        self._binary = shutil.which("wmctrl")

    def is_available(self) -> bool:
        return self._binary is not None

    def _run(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [self._binary or "wmctrl", *args],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )

    def list_windows(self) -> list[WindowInfo]:
        if not self._binary:
            return []
        try:
            result = self._run("-lp", "-x")
        except (OSError, subprocess.SubprocessError):
            return []
        if result.returncode != 0:
            return []
        active = self.active_window()
        windows: list[WindowInfo] = []
        for line in result.stdout.splitlines():
            # "wmctrl -lp -x" format: id, desktop, pid, class, host, title
            parts = line.split(" ", 5)
            if len(parts) < 6:
                continue
            try:
                window_id = int(parts[0], 16)
                pid = int(parts[2])
            except ValueError:
                continue
            wm_class = parts[3]
            title = parts[5]
            windows.append(
                WindowInfo(
                    window_id=window_id,
                    pid=pid,
                    title=title,
                    wm_class=wm_class,
                    is_active=window_id == active,
                    is_minimized="[Minimized]" in title,
                )
            )
        return windows

    def active_window(self) -> int | None:
        if not self._binary:
            return None
        try:
            result = self._run("-G")
        except (OSError, subprocess.SubprocessError):
            return None
        for line in result.stdout.splitlines():
            parts = line.split()
            if len(parts) >= 2 and parts[0] == "-1":
                try:
                    return int(parts[1], 16)
                except ValueError:
                    return None
        return None

    def activate(self, window_id: int) -> bool:
        if not self._binary:
            return False
        try:
            result = self._run("-i", "-a", hex(window_id))
        except (OSError, subprocess.SubprocessError):
            return False
        return result.returncode == 0

    def minimize(self, window_id: int) -> bool:
        if not shutil.which("xdotool"):
            return False
        try:
            result = subprocess.run(
                ["xdotool", "windowminimize", str(window_id)],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
        except (OSError, subprocess.SubprocessError):
            return False
        return result.returncode == 0

    def restore(self, window_id: int) -> bool:
        if not shutil.which("xdotool"):
            return False
        try:
            result = subprocess.run(
                ["xdotool", "windowmap", "windowraise", str(window_id)],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
        except (OSError, subprocess.SubprocessError):
            return False
        return result.returncode == 0

    def _change_state(self, window_id: int, action: str) -> bool:
        if not self._binary:
            return False
        try:
            result = self._run(
                "-i",
                "-r",
                hex(window_id),
                "-b",
                f"{action},maximized_vert,maximized_horz",
            )
        except (OSError, subprocess.SubprocessError):
            return False
        return result.returncode == 0

    def maximize(self, window_id: int) -> bool:
        return self._change_state(window_id, "add")

    def unmaximize(self, window_id: int) -> bool:
        return self._change_state(window_id, "remove")

    def close_window(self, window_id: int) -> bool:
        if not self._binary:
            return False
        try:
            result = self._run("-i", "-c", hex(window_id))
        except (OSError, subprocess.SubprocessError):
            return False
        return result.returncode == 0
