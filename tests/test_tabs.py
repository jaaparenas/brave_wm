"""Pruebas de la lectura de pestanas y su emparejamiento con las ventanas."""

from __future__ import annotations

import os
import textwrap
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

from brave_workspace_manager.models import Profile, WindowInfo
from brave_workspace_manager.tabs import FrameTabs, TabReader, emparejar, normalizar, solape


@pytest.fixture(scope="module")
def app():
    from PySide6.QtWidgets import QApplication

    return QApplication.instance() or QApplication([])


def _ventana(window_id: int, title: str, **extra) -> WindowInfo:
    return WindowInfo(window_id=window_id, pid=100, title=title, **extra)


# ------------------------------------------------------------- emparejamiento


def test_empareja_por_titulo_exacto() -> None:
    frames = [FrameTabs(title="Documentacion", titles=["A", "B"])]
    ventanas = [_ventana(1, "Otra"), _ventana(2, "Documentacion")]
    resultado = emparejar(frames, ventanas)
    assert list(resultado) == [2]
    assert resultado[2].titles == ["A", "B"]


def test_empareja_por_titulo_sin_distinguir_mayusculas() -> None:
    frames = [FrameTabs(title="  informacion   importante ", titles=["A"])]
    ventanas = [_ventana(1, "Informacion Importante")]
    assert list(emparejar(frames, ventanas)) == [1]


def test_empareja_por_geometria_cuando_el_titulo_no_coincide() -> None:
    frames = [FrameTabs(title="brave", titles=["A", "B", "C"], geometry=(100, 200, 800, 600))]
    ventanas = [_ventana(1, "Sin relacion", x=90, y=190, width=820, height=620)]
    resultado = emparejar(frames, ventanas)
    assert list(resultado) == [1]
    assert resultado[1].count == 3


def test_no_empareja_si_el_solape_es_insuficiente() -> None:
    frames = [FrameTabs(title="brave", titles=["A"], geometry=(0, 0, 100, 100))]
    ventanas = [_ventana(1, "Sin relacion", x=900, y=900, width=100, height=100)]
    assert emparejar(frames, ventanas) == {}


def test_una_sola_ventana_se_empareja_con_el_unico_frame() -> None:
    frames = [FrameTabs(title="brave", titles=["A"])]
    ventanas = [_ventana(7, "Cualquier cosa")]
    assert list(emparejar(frames, ventanas)) == [7]


def test_una_ventana_no_recibe_dos_frames() -> None:
    frames = [
        FrameTabs(title="Igual", titles=["A"], geometry=(0, 0, 100, 100)),
        FrameTabs(title="Igual", titles=["B"], geometry=(0, 0, 100, 100)),
    ]
    ventanas = [_ventana(1, "Igual", x=0, y=0, width=100, height=100)]
    assert len(emparejar(frames, ventanas)) == 1


def test_normalizar_y_solape() -> None:
    assert normalizar("  Hola   mundo ") == "hola mundo"
    assert solape((0, 0, 100, 100), (0, 0, 100, 100)) == 1.0
    assert solape((0, 0, 10, 10), (100, 100, 10, 10)) == 0.0
    assert 0 < solape((0, 0, 100, 100), (50, 0, 100, 100)) < 1


# ------------------------------------------------------------------- lector


def _ayudante(tmp_path: Path, contenido: str) -> Path:
    ruta = tmp_path / "ayudante.py"
    ruta.write_text(textwrap.dedent(contenido), encoding="utf-8")
    return ruta


def test_el_lector_interpreta_el_json(tmp_path: Path) -> None:
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


def test_el_lector_avisa_cuando_no_hay_soporte(tmp_path: Path) -> None:
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


def test_el_lector_ignora_un_json_invalido(tmp_path: Path) -> None:
    ruta = _ayudante(tmp_path, "print('esto no es json')")
    lector = TabReader(helper_path=ruta)
    assert lector.read() == []


def test_el_lector_avisa_si_falta_el_ayudante(tmp_path: Path) -> None:
    lector = TabReader(helper_path=tmp_path / "no-existe.py")
    assert lector.read() == []
    assert lector.motivo


def test_el_ayudante_real_esta_disponible() -> None:
    lector = TabReader()
    assert lector.disponible


# ------------------------------------------------------------------ interfaz


def test_el_estado_del_perfil_menciona_las_pestanas() -> None:
    perfil = Profile(id="Default", directory_name="Default", is_open=True, window_count=1)
    assert perfil.status_text == "Abierto · 1 ventana"
    perfil.tab_count = 4
    assert perfil.status_text == "Abierto · 1 ventana · 4 pestañas"


def test_la_tarjeta_muestra_el_numero_de_pestanas(app) -> None:
    from PySide6.QtWidgets import QToolButton

    from brave_workspace_manager.ui.window_panel import WindowCard

    ventana = WindowInfo(
        window_id=1,
        pid=1,
        title="Ventana",
        tab_count=3,
        tab_titles=["Primera", "Segunda", "Tercera"],
    )
    tarjeta = WindowCard(ventana, [])
    botones = tarjeta.findChildren(QToolButton)
    assert botones
    assert botones[0].text() == "3 pestañas"


def test_la_tarjeta_sin_pestanas_no_muestra_el_boton(app) -> None:
    from PySide6.QtWidgets import QToolButton

    from brave_workspace_manager.ui.window_panel import WindowCard

    tarjeta = WindowCard(WindowInfo(window_id=1, pid=1, title="Ventana"), [])
    assert not tarjeta.findChildren(QToolButton)


def test_la_tarjeta_marca_la_pestana_activa(app) -> None:
    from PySide6.QtWidgets import QLabel

    from brave_workspace_manager.ui.window_panel import WindowCard

    ventana = WindowInfo(
        window_id=1,
        pid=1,
        title="Ventana",
        tab_count=3,
        tab_titles=["Primera", "Segunda", "Tercera"],
        active_tab=1,
    )
    tarjeta = WindowCard(ventana, [])
    textos = [etiqueta.text() for etiqueta in tarjeta.findChildren(QLabel)]
    assert any(texto.startswith("▸ Segunda") for texto in textos)


def test_el_estado_de_la_pestana_activa_se_calcula_desde_el_arbol(app) -> None:
    frame = FrameTabs(title="Ventana", titles=["Primera", "Segunda"], active=1)
    assert frame.active_title == "Segunda"
    assert FrameTabs(title="Ventana", titles=["Primera"]).active_title == ""
