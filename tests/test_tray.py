"""Tests of the system tray menu and its clicks."""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QSystemTrayIcon

from brave_workspace_manager.models import Profile
from brave_workspace_manager.ui.tray import TrayIcon, profile_entry


@pytest.fixture
def profiles() -> list[Profile]:
    return [
        Profile(id="Default", directory_name="Default", brave_display_name="Alice", is_open=True),
        Profile(id="P1", directory_name="Profile 1", brave_display_name="Work", is_open=True),
        Profile(id="P2", directory_name="Profile 2", brave_display_name="Studio"),
    ]


def _texts(menu) -> list[str]:
    return [action.text() for action in menu.actions() if not action.isSeparator()]


def test_open_profiles_come_first_and_closed_ones_in_a_submenu(app, profiles) -> None:
    profiles[0].tab_count = 45
    tray = TrayIcon()
    tray.set_profiles(profiles, "Default")
    texts = _texts(tray.menu)
    assert texts[0].startswith("Alice") and "45 tabs" in texts[0]
    assert texts[1] == "Work"
    others = next(a.menu() for a in tray.menu.actions() if a.menu() is not None)
    assert _texts(others) == ["Studio"]
    assert texts[-2:] == ["Open Brave Workspace Manager", "Quit"]


def test_the_active_profile_is_checked(app, profiles) -> None:
    tray = TrayIcon()
    tray.set_profiles(profiles, "P1")
    checked = [a.text() for a in tray.menu.actions() if a.isChecked()]
    assert checked == ["Work"]


def test_choosing_a_profile_asks_to_activate_it(app, profiles) -> None:
    tray = TrayIcon()
    tray.set_profiles(profiles, None)
    received: list[str] = []
    tray.activateProfileRequested.connect(received.append)
    tray.menu.actions()[1].trigger()
    assert received == ["P1"]


def test_the_menu_is_not_rebuilt_without_changes(app, profiles) -> None:
    tray = TrayIcon()
    tray.set_profiles(profiles, "Default")
    first = tray.menu.actions()[0]
    tray.set_profiles(profiles, "Default")
    assert tray.menu.actions()[0] is first


def test_two_quick_clicks_open_the_window_maximised(app, profiles) -> None:
    tray = TrayIcon()
    received: list[str] = []
    tray.showMaximizedRequested.connect(lambda: received.append("max"))
    tray._on_activated(QSystemTrayIcon.Trigger)
    tray._on_activated(QSystemTrayIcon.Trigger)
    assert received == ["max"]
    assert not tray._click_timer.isActive()


def test_a_native_double_click_opens_the_window_maximised(app) -> None:
    tray = TrayIcon()
    received: list[str] = []
    tray.showMaximizedRequested.connect(lambda: received.append("max"))
    tray._on_activated(QSystemTrayIcon.Trigger)
    tray._on_activated(QSystemTrayIcon.DoubleClick)
    assert received == ["max"]
    assert not tray._click_timer.isActive()


def test_a_single_click_waits_for_a_possible_second_one(app) -> None:
    tray = TrayIcon()
    tray._on_activated(QSystemTrayIcon.Trigger)
    assert tray._click_timer.isActive()


def test_entry_without_tabs_is_just_the_name() -> None:
    assert profile_entry(Profile(id="x", directory_name="x", brave_display_name="X")) == "X"
