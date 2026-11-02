"""Tests of the profile gallery, its grid, its drag and drop and its summary."""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import QPoint

from brave_workspace_manager.models import Profile, WindowInfo
from brave_workspace_manager.ui.profile_gallery import (
    EXTRA_HEIGHT,
    SPACING,
    TILE_HEIGHT,
    ProfileGallery,
    ProfileSummary,
    gallery_height,
    grid_geometry,
)


@pytest.fixture
def profiles() -> list[Profile]:
    return [
        Profile(id="Default", directory_name="Default", brave_display_name="Default", is_open=True),
        Profile(id="P1", directory_name="Profile 1", brave_display_name="Profile 1"),
        Profile(
            id="P2", directory_name="Profile 2", brave_display_name="Profile 2", is_favorite=True
        ),
    ]


# ------------------------------------------------------------------- the grid


def test_without_profiles_there_is_no_grid() -> None:
    assert grid_geometry(800, 0) == (0, 0, 0, 0)


def test_columns_grow_with_the_width() -> None:
    narrow = grid_geometry(700, 12)[0]
    wide = grid_geometry(1400, 12)[0]
    assert wide > narrow


def test_the_grid_is_centred() -> None:
    available = 1200
    columns, tile_width, offset, _ = grid_geometry(available, 10)
    total = columns * tile_width + SPACING * (columns - 1)
    assert offset == (available - total) // 2
    assert total + offset <= available


def test_the_rows_cover_every_profile() -> None:
    columns, _, _, rows = grid_geometry(1200, 17)
    assert columns * rows >= 17


def test_the_height_shows_whole_rows() -> None:
    height = gallery_height(600)
    assert height % (TILE_HEIGHT + SPACING) == 0
    assert height >= 2 * TILE_HEIGHT


# ------------------------------------------------------------------ the cards


def test_the_gallery_places_the_cards(app, profiles) -> None:
    gallery = ProfileGallery()
    gallery.resize(900, 400)
    gallery.set_profiles(profiles)

    columns, width, offset, _ = grid_geometry(900, len(profiles))
    tiles = gallery._tiles
    assert len(tiles) == len(profiles)
    assert tiles[0].x() == offset
    assert tiles[0].width() == width
    assert tiles[1].x() == offset + width + SPACING
    assert columns >= 2


def test_the_gallery_rearranges_when_the_width_changes(app, profiles) -> None:
    many = profiles * 4
    gallery = ProfileGallery()
    gallery.resize(700, 400)
    gallery.set_profiles(many)
    narrow = len({tile.x() for tile in gallery._tiles})

    gallery.resize(1400, 400)
    gallery.relayout()
    wide = len({tile.x() for tile in gallery._tiles})
    assert wide > narrow


def test_the_gallery_highlights_the_active_profile(app, profiles) -> None:
    gallery = ProfileGallery()
    gallery.resize(900, 400)
    gallery.set_profiles(profiles)
    gallery.set_selected("P1")
    selected = [tile for tile in gallery._tiles if tile._selected]
    assert [tile.profile_id for tile in selected] == ["P1"]


def test_the_cards_keep_the_order_of_the_profiles(app, profiles) -> None:
    gallery = ProfileGallery()
    gallery.set_profiles(profiles)
    assert [tile.profile_id for tile in gallery._tiles] == [p.id for p in profiles]


def test_a_card_is_reused_when_the_profiles_change(app, profiles) -> None:
    """The refresh must not rebuild the cards, or a drag would be lost."""
    gallery = ProfileGallery()
    gallery.set_profiles(profiles)
    first = gallery._tiles[0]
    gallery.set_profiles(profiles)
    assert gallery._tiles[0] is first


# -------------------------------------------------------------- drag and drop


def test_the_drop_position_follows_the_grid(app, profiles) -> None:
    gallery = ProfileGallery()
    gallery.resize(900, 400)
    gallery.set_profiles(profiles)
    _, width, offset, _ = grid_geometry(900, len(profiles))
    assert gallery._index_at(QPoint(offset, 0)) == 0
    assert gallery._index_at(QPoint(offset + width + SPACING, 0)) == 1


def test_moving_a_card_reorders_the_gallery(app, profiles) -> None:
    gallery = ProfileGallery()
    gallery.resize(900, 400)
    gallery.set_profiles(profiles)
    received: list[list[str]] = []
    gallery.reordered.connect(received.append)

    gallery._move("P2", 0)

    assert [tile.profile_id for tile in gallery._tiles] == ["P2", "Default", "P1"]
    assert received == [["P2", "Default", "P1"]]


def test_moving_an_unknown_card_does_nothing(app, profiles) -> None:
    gallery = ProfileGallery()
    gallery.set_profiles(profiles)
    received: list[list[str]] = []
    gallery.reordered.connect(received.append)

    gallery._move("missing", 0)

    assert received == []
    assert [tile.profile_id for tile in gallery._tiles] == [p.id for p in profiles]


# ---------------------------------------------------------- unassigned card


def test_the_unassigned_card_is_the_last_one_of_the_gallery(app, profiles) -> None:
    gallery = ProfileGallery()
    gallery.resize(900, 400)
    gallery.set_profiles(profiles)
    _, _, _, rows = grid_geometry(900, len(profiles))
    assert gallery.unassigned_card.y() >= rows * (TILE_HEIGHT + SPACING)
    assert gallery.unassigned_card.height() == EXTRA_HEIGHT


def test_the_unassigned_card_lists_the_windows_without_profile(app, profiles) -> None:
    gallery = ProfileGallery()
    windows = [
        WindowInfo(window_id=1, pid=1, title="One", tab_count=2),
        WindowInfo(window_id=2, pid=1, title="Two"),
    ]
    gallery.set_unassigned(windows, profiles)
    combo = gallery.unassigned_card._window_combo
    assert combo.count() == 2
    assert combo.itemData(0) == 1


def test_the_unassigned_card_asks_to_save_a_new_profile(app, profiles) -> None:
    gallery = ProfileGallery()
    gallery.set_unassigned([WindowInfo(window_id=7, pid=1, title="Loose")], profiles)
    received: list[tuple[int, str]] = []
    gallery.saveProfileRequested.connect(
        lambda window_id, title: received.append((window_id, title))
    )

    gallery.unassigned_card._emit_save()

    assert received == [(7, "Loose")]


def test_the_unassigned_card_asks_to_assign_a_window(app, profiles) -> None:
    gallery = ProfileGallery()
    gallery.set_unassigned([WindowInfo(window_id=7, pid=1, title="Loose")], profiles)
    received: list[tuple[int, str]] = []
    gallery.assignRequested.connect(
        lambda window_id, profile_id: received.append((window_id, profile_id))
    )

    combo = gallery.unassigned_card._assign_combo
    combo.setCurrentIndex(1)

    assert received == [(7, "Default")]


# ---------------------------------------------------------------- the summary


def test_the_summary_counts_the_profiles(app, profiles) -> None:
    summary = ProfileSummary()
    windows = [
        WindowInfo(window_id=1, pid=1, profile_id="Default"),
        WindowInfo(window_id=2, pid=1, profile_id=None),
    ]
    summary.update_summary(profiles, windows, "Default")

    values = summary.snapshot()
    assert values["total"] == "3"
    assert values["open"] == "1"
    assert values["closed"] == "2"
    assert values["favorites"] == "1"
    assert values["windows"] == "2"
    assert values["unassigned"] == "1"
    assert summary._active.text() == "Default"


def test_the_summary_without_profiles_does_not_fail(app) -> None:
    summary = ProfileSummary()
    summary.update_summary([], [], "")
    assert summary.snapshot()["total"] == "0"
    assert summary._active.text() == "—"


def test_local_shortcuts_are_not_duplicated(app, tmp_path) -> None:
    """Two shortcuts with the same keys are ambiguous and Qt fires neither."""
    from PySide6.QtGui import QShortcut

    from brave_workspace_manager.core.controller import AppController
    from brave_workspace_manager.database import Database
    from brave_workspace_manager.ui.main_window import MainWindow

    class Backend:
        name = "test"

        def list_windows(self):
            return []

    class Launcher:
        available = False

    database = Database(tmp_path / "w.db")
    database.set_setting("hotkeys_enabled", "0")
    controller = AppController(database, Backend(), Launcher(), user_data_dir=tmp_path)
    window = MainWindow(controller, database)
    window.start()
    app.processEvents()
    active = [s for s in window.findChildren(QShortcut) if s.isEnabled()]
    keys = [s.key().toString() for s in active]
    assert len(keys) == len(set(keys))
    controller.stop()
    database.close()
