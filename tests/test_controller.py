"""Pruebas del filtrado de ventanas de Brave del controlador."""

from __future__ import annotations

import os

from brave_workspace_manager.core.controller import AppController
from brave_workspace_manager.database import Database
from brave_workspace_manager.models import BrowserProcess, Profile, WindowInfo
from brave_workspace_manager.tabs import FrameTabs


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


def test_avisa_si_brave_no_expone_las_pestanas(tmp_path) -> None:
    controller = _controller(tmp_path, [])
    controller._navegador_abierto = True
    controller._sin_accesibilidad = {7}
    assert "accesibilidad" in controller.tabs_status


def test_sin_aviso_cuando_el_navegador_expone_las_pestanas(tmp_path) -> None:
    controller = _controller(tmp_path, [])
    controller._navegador_abierto = True
    controller._sin_accesibilidad = set()
    assert controller.tabs_status == ""


def test_desactivar_la_lectura_no_muestra_avisos(tmp_path) -> None:
    controller = _controller(tmp_path, [])
    controller._navegador_abierto = True
    controller._sin_accesibilidad = {7}
    controller.set_read_tabs(False)
    assert controller.tabs_status == ""


def test_las_pestanas_se_reparten_entre_ventanas_y_perfiles(tmp_path) -> None:
    controller = _controller(tmp_path, [])
    ventana = WindowInfo(window_id=7, pid=1, profile_id="Default")
    controller.windows = [ventana]
    controller.profiles = [Profile(id="Default", directory_name="Default")]
    frame = FrameTabs(title="Ventana", titles=["A", "B", "C"], active=1)
    controller._aplicar_pestanas([ventana], [frame])
    assert ventana.tab_count == 3
    assert ventana.tab_titles == ["A", "B", "C"]
    assert ventana.active_tab == 1
    assert controller.profiles[0].tab_count == 3
