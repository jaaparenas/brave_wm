"""Pruebas de la capa de persistencia SQLite."""

from __future__ import annotations

from pathlib import Path

from brave_workspace_manager.database import Database
from brave_workspace_manager.models import Profile


def test_saves_and_loads_profile(tmp_path: Path) -> None:
    database = Database(tmp_path / "workspace.db")
    profile = Profile(
        id="Profile 1",
        directory_name="Profile 1",
        display_name="Work",
        color="#ff0000",
        icon="star",
        sort_order=3,
        is_favorite=True,
    )
    database.save_profile(profile)
    stored = database.load_profiles()["Profile 1"]
    assert stored.display_name == "Work"
    assert stored.color == "#ff0000"
    assert stored.icon == "star"
    assert stored.sort_order == 3
    assert stored.is_favorite is True


def test_save_profile_is_idempotent(tmp_path: Path) -> None:
    database = Database(tmp_path / "workspace.db")
    profile = Profile(id="Default", directory_name="Default", display_name="A")
    database.save_profile(profile)
    profile.display_name = "B"
    database.save_profile(profile)
    assert len(database.load_profiles()) == 1
    assert database.load_profiles()["Default"].display_name == "B"


def test_settings_round_trip(tmp_path: Path) -> None:
    database = Database(tmp_path / "workspace.db")
    assert database.get_setting("poll_interval", "2000") == "2000"
    database.set_setting("poll_interval", "500")
    assert database.get_setting("poll_interval") == "500"


def test_window_assignments_are_keyed_by_window_and_pid(tmp_path: Path) -> None:
    database = Database(tmp_path / "workspace.db")
    database.assign_window(0x1001, 42, "Default", "Titulo", "learned")
    assignments = database.load_assignments()
    assert assignments[(0x1001, 42)]["profile_id"] == "Default"
    assert (0x1001, 43) not in assignments


def test_assign_window_updates_existing_row(tmp_path: Path) -> None:
    database = Database(tmp_path / "workspace.db")
    database.assign_window(0x1001, 42, "Default", "Titulo", "learned")
    database.assign_window(0x1001, 42, "Profile 1", "Titulo", "manual")
    assignments = database.load_assignments()
    assert len(assignments) == 1
    assert assignments[(0x1001, 42)]["profile_id"] == "Profile 1"
    assert assignments[(0x1001, 42)]["method"] == "manual"


def test_clear_assignments_for_browser_process(tmp_path: Path) -> None:
    database = Database(tmp_path / "workspace.db")
    database.assign_window(1, 42, "Default")
    database.assign_window(2, 43, "Default")
    database.clear_assignments(42)
    assert list(database.load_assignments()) == [(2, 43)]


def test_delete_profile_removes_its_assignments(tmp_path: Path) -> None:
    database = Database(tmp_path / "workspace.db")
    database.save_profile(Profile(id="Default", directory_name="Default"))
    database.assign_window(1, 42, "Default")
    database.delete_profile("Default")
    assert database.load_profiles() == {}
    assert database.load_assignments() == {}


def test_next_sort_order(tmp_path: Path) -> None:
    database = Database(tmp_path / "workspace.db")
    assert database.next_sort_order() == 0
    database.save_profile(Profile(id="Default", directory_name="Default", sort_order=0))
    assert database.next_sort_order() == 1
