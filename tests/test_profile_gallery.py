"""Pruebas de la galeria de perfiles y del resumen."""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

from brave_workspace_manager.models import Profile, WindowInfo
from brave_workspace_manager.ui.profile_gallery import (
    SPACING,
    TILE_HEIGHT,
    ProfileGallery,
    ProfileSummary,
    gallery_height,
    grid_geometry,
)


@pytest.fixture(scope="module")
def app():
    from PySide6.QtWidgets import QApplication

    return QApplication.instance() or QApplication([])


@pytest.fixture
def perfiles() -> list[Profile]:
    return [
        Profile(id="Default", directory_name="Default", brave_display_name="Default", is_open=True),
        Profile(id="P1", directory_name="Profile 1", brave_display_name="Profile 1"),
        Profile(
            id="P2", directory_name="Profile 2", brave_display_name="Profile 2", is_favorite=True
        ),
    ]


# ------------------------------------------------------------- calculo de la rejilla


def test_sin_perfiles_no_hay_rejilla() -> None:
    assert grid_geometry(800, 0) == (0, 0, 0, 0)


def test_las_columnas_crecen_con_el_ancho() -> None:
    columnas_estrechas = grid_geometry(700, 12)[0]
    columnas_anchas = grid_geometry(1400, 12)[0]
    assert columnas_anchas > columnas_estrechas


def test_la_rejilla_esta_centrada() -> None:
    available = 1200
    columns, tile_width, offset, _ = grid_geometry(available, 10)
    ancho_total = columns * tile_width + SPACING * (columns - 1)
    assert offset == (available - ancho_total) // 2
    assert ancho_total + offset <= available


def test_las_filas_cubren_todos_los_perfiles() -> None:
    columns, _, _, rows = grid_geometry(1200, 17)
    assert columns * rows >= 17


def test_la_altura_muestra_filas_completas() -> None:
    alto = gallery_height(600)
    assert alto % (TILE_HEIGHT + SPACING) == 0
    assert alto >= 2 * TILE_HEIGHT


# ------------------------------------------------------------- widgets


def test_la_galeria_coloca_las_fichas(app, perfiles) -> None:
    galeria = ProfileGallery()
    galeria.resize(900, 400)
    galeria.set_profiles(perfiles)

    columnas, ancho, offset, _ = grid_geometry(900, len(perfiles))
    fichas = galeria._tiles
    assert len(fichas) == len(perfiles)
    assert fichas[0].x() == offset
    assert fichas[0].width() == ancho
    assert fichas[1].x() == offset + ancho + SPACING
    assert columnas >= 2


def test_la_galeria_se_reorganiza_al_cambiar_el_ancho(app, perfiles) -> None:
    muchos = perfiles * 4
    galeria = ProfileGallery()
    galeria.resize(700, 400)
    galeria.set_profiles(muchos)
    estrechas = len({tile.x() for tile in galeria._tiles})

    galeria.resize(1400, 400)
    galeria.relayout()
    anchas = len({tile.x() for tile in galeria._tiles})
    assert anchas > estrechas


def test_la_galeria_resalta_el_perfil_activo(app, perfiles) -> None:
    galeria = ProfileGallery()
    galeria.resize(900, 400)
    galeria.set_profiles(perfiles)
    galeria.set_selected("P1")
    seleccionados = [tile for tile in galeria._tiles if tile._selected]
    assert [tile.profile_id for tile in seleccionados] == ["P1"]


def test_el_resumen_cuenta_los_perfiles(app, perfiles) -> None:
    resumen = ProfileSummary()
    ventanas = [
        WindowInfo(window_id=1, pid=1, profile_id="Default"),
        WindowInfo(window_id=2, pid=1, profile_id=None),
    ]
    resumen.update_summary(perfiles, ventanas, "Default")

    valores = resumen.snapshot()
    assert valores["total"] == "3"
    assert valores["open"] == "1"
    assert valores["closed"] == "2"
    assert valores["favorites"] == "1"
    assert valores["windows"] == "2"
    assert valores["unassigned"] == "1"
    assert resumen._active.text() == "Default"


def test_el_resumen_sin_perfiles_no_falla(app) -> None:
    resumen = ProfileSummary()
    resumen.update_summary([], [], "")
    assert resumen.snapshot()["total"] == "0"
    assert resumen._active.text() == "—"
