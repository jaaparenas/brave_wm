"""Pruebas del ayudante de accesibilidad con un arbol de accesibilidad simulado."""

from __future__ import annotations

import sys
import types

import pytest

from brave_workspace_manager import a11y_helper


class _Extents:
    def __init__(self, x: int, y: int, width: int, height: int) -> None:
        self.x = x
        self.y = y
        self.width = width
        self.height = height


class _ConjuntoEstados:
    def __init__(self, estados: tuple[str, ...]) -> None:
        self._estados = estados

    def contains(self, estado: str) -> bool:
        return estado in self._estados


class _Nodo:
    def __init__(
        self,
        role: str,
        name: str = "",
        children: list | None = None,
        estados: tuple[str, ...] = (),
    ) -> None:
        self._role = role
        self._name = name
        self._children = children or []
        self._estados = estados

    def get_role_name(self) -> str:
        return self._role

    def get_name(self) -> str:
        return self._name

    def get_child_count(self) -> int:
        return len(self._children)

    def get_child_at_index(self, indice: int):
        return self._children[indice]

    def get_state_set(self) -> _ConjuntoEstados:
        return _ConjuntoEstados(self._estados)

    def get_extents(self, _tipo):
        return _Extents(100, 200, 800, 600)


class _AtspiFalso:
    CoordType = types.SimpleNamespace(SCREEN="screen")
    StateType = types.SimpleNamespace(SHOWING="showing", SELECTED="selected")

    def __init__(self, escritorio: _Nodo) -> None:
        self._escritorio = escritorio

    def get_desktop(self, _indice: int) -> _Nodo:
        return self._escritorio


def _arbol() -> _Nodo:
    pestanas_reales = _Nodo(
        "page tab list",
        children=[
            _Nodo("page tab", "Primera"),
            _Nodo("page tab", "Segunda", estados=("selected",)),
            _Nodo("page tab", "Tercera"),
        ],
        estados=("showing",),
    )
    # Franja vacia y oculta: Chromium deja una segunda, que no debe ganar.
    franja_vacia = _Nodo("page tab list", children=[_Nodo("panel")])
    barra = _Nodo("tool bar", children=[pestanas_reales, franja_vacia])
    contenido_web = _Nodo(
        "document web",
        children=[_Nodo("page tab list", children=[_Nodo("page tab", "Pestana de la pagina")])],
    )
    frame = _Nodo("frame", "Ventana de prueba", children=[barra, contenido_web])
    aplicacion = _Nodo("application", "brave", children=[frame])
    return _Nodo("application", "desktop", children=[aplicacion, _Nodo("application", "otro")])


@pytest.fixture
def atspi(monkeypatch):
    """Inyecta un modulo gi simulado para no depender del escritorio real."""
    modulo_gi = types.ModuleType("gi")
    modulo_gi.require_version = lambda *_args: None
    modulo_repository = types.ModuleType("gi.repository")
    modulo_repository.Atspi = _AtspiFalso(_arbol())
    monkeypatch.setitem(sys.modules, "gi", modulo_gi)
    monkeypatch.setitem(sys.modules, "gi.repository", modulo_repository)
    return modulo_repository.Atspi


def test_encuentra_las_pestanas_de_la_franja(atspi) -> None:
    frames = a11y_helper._frames_de_brave(atspi)
    assert len(frames) == 1
    assert frames[0]["title"] == "Ventana de prueba"
    assert frames[0]["tabs"] == ["Primera", "Segunda", "Tercera"]
    assert frames[0]["geometry"] == [100, 200, 800, 600]


def test_ignora_las_pestanas_del_contenido_web(atspi) -> None:
    frames = a11y_helper._frames_de_brave(atspi)
    assert "Pestana de la pagina" not in frames[0]["tabs"]


def test_informa_cual_es_la_pestana_activa(atspi) -> None:
    frames = a11y_helper._frames_de_brave(atspi)
    assert frames[0]["active"] == 1


def test_sin_pestanas_no_hay_activa(atspi) -> None:
    escritorio = _Nodo(
        "application",
        "desktop",
        children=[
            _Nodo(
                "application",
                "brave",
                children=[_Nodo("frame", "Ventana", children=[_Nodo("panel")])],
            )
        ],
    )
    frames = a11y_helper._frames_de_brave(_AtspiFalso(escritorio))
    assert frames[0]["tabs"] == []
    assert frames[0]["active"] == -1


def test_prefiere_la_franja_con_pestanas(atspi) -> None:
    frame = _arbol().get_child_at_index(0).get_child_at_index(0)
    listas = a11y_helper._listas_de_pestanas(frame, atspi)
    assert len(listas) == 2
    assert a11y_helper._mejor_franja(frame, atspi) == [
        ("Primera", False),
        ("Segunda", True),
        ("Tercera", False),
    ]


def test_sin_aplicaciones_devuelve_lista_vacia(atspi) -> None:
    vacio = _AtspiFalso(_Nodo("application", "desktop", children=[]))
    assert a11y_helper._frames_de_brave(vacio) == []


def test_el_ayudante_responde_json(atspi, capsys) -> None:
    a11y_helper.main()
    salida = capsys.readouterr().out
    assert '"ok": true' in salida
    assert "Primera" in salida
    assert '"active": 1' in salida
