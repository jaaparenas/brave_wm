"""Tests of the tab reading and its matching with the windows."""

from __future__ import annotations

import os
import textwrap
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


from brave_workspace_manager.models import Profile, WindowInfo
from brave_workspace_manager.tabs import FrameTabs, TabReader, emparejar, normalizar, solape


def _ventana(window_id: int, title: str, **extra) -> WindowInfo:
    return WindowInfo(window_id=window_id, pid=100, title=title, **extra)


# ------------------------------------------------------------- matching


def test_matches_by_exact_title() -> None:
    frames = [FrameTabs(title="Documentacion", titles=["A", "B"])]
    ventanas = [_ventana(1, "Otra"), _ventana(2, "Documentacion")]
    resultado = emparejar(frames, ventanas)
    assert list(resultado) == [2]
    assert resultado[2].titles == ["A", "B"]


def test_matches_by_title_ignoring_case() -> None:
    frames = [FrameTabs(title="  informacion   importante ", titles=["A"])]
    ventanas = [_ventana(1, "Informacion Importante")]
    assert list(emparejar(frames, ventanas)) == [1]


def test_matches_by_geometry_when_the_title_differs() -> None:
    frames = [FrameTabs(title="brave", titles=["A", "B", "C"], geometry=(100, 200, 800, 600))]
    ventanas = [_ventana(1, "Sin relacion", x=90, y=190, width=820, height=620)]
    resultado = emparejar(frames, ventanas)
    assert list(resultado) == [1]
    assert resultado[1].count == 3


def test_no_match_when_the_overlap_is_too_small() -> None:
    frames = [FrameTabs(title="brave", titles=["A"], geometry=(0, 0, 100, 100))]
    ventanas = [_ventana(1, "Sin relacion", x=900, y=900, width=100, height=100)]
    assert emparejar(frames, ventanas) == {}


def test_a_single_window_matches_the_only_frame() -> None:
    frames = [FrameTabs(title="brave", titles=["A"])]
    ventanas = [_ventana(7, "Cualquier cosa")]
    assert list(emparejar(frames, ventanas)) == [7]


def test_a_window_never_gets_two_frames() -> None:
    frames = [
        FrameTabs(title="Igual", titles=["A"], geometry=(0, 0, 100, 100)),
        FrameTabs(title="Igual", titles=["B"], geometry=(0, 0, 100, 100)),
    ]
    ventanas = [_ventana(1, "Igual", x=0, y=0, width=100, height=100)]
    assert len(emparejar(frames, ventanas)) == 1


def test_normalise_and_overlap() -> None:
    assert normalizar("  Hola   mundo ") == "hola mundo"
    assert solape((0, 0, 100, 100), (0, 0, 100, 100)) == 1.0
    assert solape((0, 0, 10, 10), (100, 100, 10, 10)) == 0.0
    assert 0 < solape((0, 0, 100, 100), (50, 0, 100, 100)) < 1


# ------------------------------------------------------------------- reader


def _ayudante(tmp_path: Path, contenido: str) -> Path:
    ruta = tmp_path / "ayudante.py"
    ruta.write_text(textwrap.dedent(contenido), encoding="utf-8")
    return ruta


def test_the_reader_parses_the_json(tmp_path: Path) -> None:
    ruta = _ayudante(
        tmp_path,
        """
        import json
        print(json.dumps({
            "ok": True,
            "frames": [{"title": "Ventana", "tabs": ["A", "B"], "geometry": [1, 2, 3, 4]}],
        }))
        """,
    )
    lector = TabReader(helper_path=ruta)
    frames = lector.read()
    assert len(frames) == 1
    assert frames[0].titles == ["A", "B"]
    assert frames[0].geometry == (1, 2, 3, 4)
    assert frames[0].count == 2


def test_the_reader_reports_missing_support(tmp_path: Path) -> None:
    ruta = _ayudante(
        tmp_path,
        """
        import json
        print(json.dumps({"ok": False, "reason": "atspi-no-disponible"}))
        """,
    )
    lector = TabReader(helper_path=ruta)
    assert lector.read() == []
    assert "atspi" in lector.motivo


def test_the_reader_ignores_invalid_json(tmp_path: Path) -> None:
    ruta = _ayudante(tmp_path, "print('esto no es json')")
    lector = TabReader(helper_path=ruta)
    assert lector.read() == []


def test_the_reader_reports_a_missing_helper(tmp_path: Path) -> None:
    lector = TabReader(helper_path=tmp_path / "no-existe.py")
    assert lector.read() == []
    assert lector.motivo


def test_the_real_helper_is_available() -> None:
    lector = TabReader()
    assert lector.disponible


# ------------------------------------------------------------------ interface


def test_the_profile_status_mentions_the_tabs() -> None:
    perfil = Profile(id="Default", directory_name="Default", is_open=True, window_count=1)
    assert perfil.status_text == "Open · 1 window"
    perfil.tab_count = 4
    assert perfil.status_text == "Open · 1 window · 4 tabs"


def test_the_card_shows_the_number_of_tabs(app) -> None:
    from brave_workspace_manager.ui.profile_tab import ProfileTab

    perfil = Profile(id="Default", directory_name="Default", is_open=True, window_count=1)
    perfil.tab_count = 3
    tarjeta = ProfileTab(perfil)
    tarjeta.resize(200, ProfileTab.HEIGHT)
    tarjeta.set_windows([WindowInfo(window_id=1, pid=1, title="Ventana", tab_count=3)])
    assert "3 tabs" in tarjeta._tabs.text()


def test_a_closed_card_disables_its_buttons(app) -> None:
    from brave_workspace_manager.ui.profile_tab import ProfileTab

    tarjeta = ProfileTab(Profile(id="Default", directory_name="Default"))
    assert all(not boton.isEnabled() for boton in tarjeta._buttons.values())
    assert tarjeta._tabs.text() == ""


def test_the_buttons_act_on_the_profile_window(app) -> None:
    from brave_workspace_manager.ui.profile_tab import ProfileTab

    perfil = Profile(id="Default", directory_name="Default", is_open=True, window_count=2)
    tarjeta = ProfileTab(perfil)
    tarjeta.set_windows(
        [
            WindowInfo(window_id=1, pid=1, title="Fondo"),
            WindowInfo(window_id=2, pid=1, title="Activa", is_active=True),
        ]
    )
    recibidas: list[tuple[str, int, str]] = []
    tarjeta.windowActionRequested.connect(lambda p, w, a: recibidas.append((p, w, a)))
    for accion in ("minimize", "maximize", "close"):
        tarjeta._buttons[accion].click()
    assert recibidas == [
        ("Default", 2, "minimize"),
        ("Default", 2, "maximize"),
        ("Default", 2, "close"),
    ]


def test_the_active_tab_comes_from_the_tree(app) -> None:
    frame = FrameTabs(title="Ventana", titles=["Primera", "Segunda"], active=1)
    assert frame.active_title == "Segunda"
    assert FrameTabs(title="Ventana", titles=["Primera"]).active_title == ""


def test_the_minimise_button_restores_a_minimised_window(app) -> None:
    from brave_workspace_manager.ui.profile_tab import ProfileTab

    perfil = Profile(id="Profile 1", directory_name="Profile 1", is_open=True, window_count=1)
    tarjeta = ProfileTab(perfil)
    tarjeta.set_windows([WindowInfo(window_id=5, pid=1, is_minimized=True, is_maximized=True)])
    recibidas: list[str] = []
    tarjeta.windowActionRequested.connect(lambda _p, _w, a: recibidas.append(a))
    tarjeta._buttons["minimize"].click()
    assert recibidas == ["restore"]


def test_the_card_offers_the_other_profiles(app) -> None:
    from brave_workspace_manager.ui.profile_tab import ProfileTab

    tarjeta = ProfileTab(Profile(id="Default", directory_name="Default"))
    tarjeta.set_profile_choices([("Default", "Alice"), ("Profile 1", "Work")])
    assert tarjeta._choices == [("Profile 1", "Work")]


# ------------------------------------------------- profile from the a11y tree


def test_the_frame_reveals_its_profile() -> None:
    frame = FrameTabs(title="Dashboard - Brave – Alice Doe")
    assert frame.profile_name == "Alice Doe"
    assert frame.window_title == "Dashboard - Brave"


def test_an_en_dash_inside_the_page_title_is_not_a_profile() -> None:
    frame = FrameTabs(title="News – Today - Brave")
    assert frame.profile_name == ""
    assert frame.window_title == "News – Today - Brave"


def test_frames_with_a_profile_suffix_match_their_window() -> None:
    frames = [
        FrameTabs(title="Dashboard - Brave – Alice Doe"),
        FrameTabs(
            title="(4) Chat | Teams - High memory usage - 885 MB - Brave – Work",
        ),
    ]
    ventanas = [_ventana(1, "(4) Chat | Teams - Brave"), _ventana(2, "Dashboard - Brave")]
    resultado = emparejar(frames, ventanas)
    assert resultado[2].profile_name == "Alice Doe"
    assert resultado[1].profile_name == "Work"
