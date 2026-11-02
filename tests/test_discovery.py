"""Tests of the discovery of native profiles."""

from __future__ import annotations

import json
from pathlib import Path

from brave_workspace_manager import discovery


def test_discovers_only_real_profiles(fake_brave_root: Path) -> None:
    found = discovery.discover_profiles(fake_brave_root)
    assert [item.directory_name for item in found] == ["Default", "Profile 1"]


def test_reads_visible_names_from_local_state(fake_brave_root: Path) -> None:
    found = {item.directory_name: item for item in discovery.discover_profiles(fake_brave_root)}
    assert found["Default"].display_name == "Alice Doe"
    assert found["Profile 1"].display_name == "Work"


def test_ignores_missing_or_broken_local_state(tmp_path: Path) -> None:
    assert discovery.read_local_state(tmp_path) == {}
    assert discovery.discover_profiles(tmp_path) == []


def test_invalid_local_state_does_not_raise(tmp_path: Path) -> None:
    (tmp_path / "Local State").write_text("{no es json", encoding="utf-8")
    assert discovery.read_local_state(tmp_path) == {}


def test_last_used_and_active_profiles(fake_brave_root: Path) -> None:
    assert discovery.last_used_profile(fake_brave_root) == "Default"
    assert discovery.last_active_profiles(fake_brave_root) == ["Default", "Profile 1"]


def test_profile_sort_key_orders_numerically() -> None:
    names = ["Profile 10", "Profile 2", "Default", "Profile 1"]
    assert sorted(names, key=discovery.profile_sort_key) == [
        "Default",
        "Profile 1",
        "Profile 2",
        "Profile 10",
    ]


def test_prettify_directory() -> None:
    assert discovery.prettify_directory("Default") == "Default"
    assert discovery.prettify_directory("mi-perfil") == "Mi Perfil"


def test_never_writes_to_the_profile_directory(fake_brave_root: Path) -> None:
    before = {path.name for path in fake_brave_root.rglob("*")}
    discovery.discover_profiles(fake_brave_root)
    discovery.read_local_state(fake_brave_root)
    after = {path.name for path in fake_brave_root.rglob("*")}
    assert before == after


def test_avatar_path_is_ignored_when_missing(fake_brave_root: Path) -> None:
    state_path = fake_brave_root / "Local State"
    data = json.loads(state_path.read_text())
    data["profile"]["info_cache"]["Default"]["avatar_icon"] = "no/existe.png"
    state_path.write_text(json.dumps(data), encoding="utf-8")
    found = {item.directory_name: item for item in discovery.discover_profiles(fake_brave_root)}
    assert found["Default"].avatar_path is None
