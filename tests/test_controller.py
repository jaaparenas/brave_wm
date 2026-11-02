"""Pruebas del filtrado de ventanas de Brave del controlador."""

from __future__ import annotations

import os

from brave_workspace_manager.core.controller import AppController
from brave_workspace_manager.database import Database
from brave_workspace_manager.models import BrowserProcess, WindowInfo


class _FakeBackend:
    def __init__(self, windows: list[WindowInfo]) -> None:
        self._windows = windows

    def list_windows(self) -> list[WindowInfo]:
        return list(self._windows)


class _FakeLauncher:
    def available(self) -> bool:
        return False

    def open_profile_manager(self) -> bool:
        return False


def _controller(tmp_path, windows: list[WindowInfo]) -> AppController:
    database = Database(tmp_path / "workspace.db")
    return AppController(database, _FakeBackend(windows), _FakeLauncher())


def test_keeps_windows_of_the_browser_process(tmp_path) -> None:
    controller = _controller(
        tmp_path,
        [WindowInfo(window_id=1, pid=4242, wm_class="brave-browser brave-browser")],
    )
    procesos = [BrowserProcess(pid=4242, kind="browser")]
    assert [w.window_id for w in controller._brave_windows(procesos)] == [1]


def test_keeps_windows_recognised_by_their_class(tmp_path) -> None:
    controller = _controller(
        tmp_path,
        [WindowInfo(window_id=2, pid=999, wm_class="brave-browser Brave-browser")],
    )
    assert [w.window_id for w in controller._brave_windows([])] == [2]


def test_ignores_other_applications(tmp_path) -> None:
    controller = _controller(
        tmp_path,
        [
            WindowInfo(window_id=3, pid=111, wm_class="code code"),
            WindowInfo(window_id=4, pid=222, wm_class="nemo-desktop nemo-desktop"),
        ],
    )
    assert controller._brave_windows([]) == []


def test_ignores_its_own_window(tmp_path) -> None:
    """La ventana de la aplicacion no es una ventana de Brave."""
    controller = _controller(
        tmp_path,
        [
            WindowInfo(
                window_id=5,
                pid=os.getpid(),
                title="Brave Workspace Manager",
                wm_class="__main__.py Brave Workspace Manager",
            )
        ],
    )
    assert controller._brave_windows([]) == []
