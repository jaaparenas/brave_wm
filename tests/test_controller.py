"""Tests of the application controller."""

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
    """The window of the application is not a Brave window."""
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


def test_warns_when_brave_hides_the_tabs(tmp_path) -> None:
    controller = _controller(tmp_path, [])
    controller._needs_a11y = True
    controller._a11y_failed = True
    assert "accessibility" in controller.tabs_status.lower()


def test_no_warning_when_the_browser_exposes_the_tabs(tmp_path) -> None:
    controller = _controller(tmp_path, [])
    controller._needs_a11y = False
    controller._a11y_failed = False
    assert controller.tabs_status == ""


def test_disabled_tab_reading_shows_no_warning(tmp_path) -> None:
    controller = _controller(tmp_path, [])
    controller._needs_a11y = True
    controller._a11y_failed = True
    controller.set_read_tabs(False)
    assert controller.tabs_status == ""


def test_tabs_are_shared_between_windows_and_profiles(tmp_path) -> None:
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


# ------------------------------------------------------- new card features


class _ActionBackend(_FakeBackend):
    """Backend that records the actions it receives."""

    name = "fake"

    def __init__(self, windows: list[WindowInfo]) -> None:
        super().__init__(windows)
        self.calls: list[tuple[str, int]] = []

    def _record(self, action: str, window_id: int) -> bool:
        self.calls.append((action, window_id))
        return True

    def activate(self, window_id: int) -> bool:
        return self._record("activate", window_id)

    def minimize(self, window_id: int) -> bool:
        return self._record("minimize", window_id)

    def restore(self, window_id: int) -> bool:
        return self._record("restore", window_id)

    def maximize(self, window_id: int) -> bool:
        return self._record("maximize", window_id)

    def unmaximize(self, window_id: int) -> bool:
        return self._record("unmaximize", window_id)

    def close_window(self, window_id: int) -> bool:
        return self._record("close", window_id)


def _action_controller(tmp_path, windows: list[WindowInfo]) -> tuple[AppController, _ActionBackend]:
    backend = _ActionBackend(windows)
    controller = AppController(
        Database(tmp_path / "workspace.db"),
        backend,
        _FakeLauncher(),
        user_data_dir=tmp_path / "missing-brave",
    )
    controller.refresh = lambda: None
    controller.windows = list(windows)
    return controller, backend


def test_window_actions_reach_the_backend(tmp_path) -> None:
    window = WindowInfo(window_id=9, pid=1)
    controller, backend = _action_controller(tmp_path, [window])
    for action in ("activate", "minimize", "restore", "maximize", "close"):
        assert controller.window_action(9, action)
    assert [name for name, _ in backend.calls] == [
        "activate",
        "minimize",
        "restore",
        "maximize",
        "close",
    ]


def test_maximize_toggles_a_maximized_window(tmp_path) -> None:
    controller, backend = _action_controller(
        tmp_path, [WindowInfo(window_id=9, pid=1, is_maximized=True)]
    )
    controller.window_action(9, "maximize")
    assert backend.calls == [("unmaximize", 9)]


def test_unknown_window_or_action_is_ignored(tmp_path) -> None:
    controller, backend = _action_controller(tmp_path, [WindowInfo(window_id=9, pid=1)])
    assert not controller.window_action(1234, "close")
    assert not controller.window_action(9, "explode")
    assert backend.calls == []


def test_reorder_profiles_persists_the_new_order(tmp_path) -> None:
    controller, _ = _action_controller(tmp_path, [])
    controller.profiles = [
        Profile(id="A", directory_name="A", sort_order=0),
        Profile(id="B", directory_name="B", sort_order=1),
        Profile(id="C", directory_name="C", sort_order=2),
    ]
    controller.reorder_profiles(["C", "A", "B"])
    assert [p.id for p in controller.profiles] == ["C", "A", "B"]
    stored = controller.database.load_profiles()
    assert stored["C"].sort_order == 0
    assert stored["B"].sort_order == 2


def test_profile_image_is_copied_and_removed(tmp_path, monkeypatch) -> None:
    from brave_workspace_manager.core import controller as module

    monkeypatch.setattr(module, "data_dir", lambda: tmp_path / "data")
    controller, _ = _action_controller(tmp_path, [])
    controller.profiles = [Profile(id="Default", directory_name="Default")]
    source = tmp_path / "me.png"
    source.write_bytes(b"\x89PNG fake")

    assert controller.set_profile_image("Default", str(source))
    copied = controller.profiles[0].custom_image
    assert copied.startswith(str(tmp_path / "data" / "images"))
    assert (tmp_path / "data" / "images" / "Default.png").read_bytes() == b"\x89PNG fake"

    assert controller.set_profile_image("Default", None)
    assert controller.profiles[0].custom_image == ""
    assert not (tmp_path / "data" / "images" / "Default.png").exists()


def test_profile_image_rejects_other_files(tmp_path) -> None:
    controller, _ = _action_controller(tmp_path, [])
    controller.profiles = [Profile(id="Default", directory_name="Default")]
    document = tmp_path / "notes.txt"
    document.write_text("hello", encoding="utf-8")
    assert not controller.set_profile_image("Default", str(document))
    assert not controller.set_profile_image("Default", str(tmp_path / "missing.png"))


def test_an_unassigned_window_becomes_a_new_profile(tmp_path) -> None:
    window = WindowInfo(window_id=9, pid=77, title="Work stuff")
    controller, _ = _action_controller(tmp_path, [window])
    profile_id = controller.save_window_as_profile(9, "Work")
    assert profile_id == "virtual-1"
    stored = controller.database.load_profiles()[profile_id]
    assert stored.is_virtual
    assert stored.display_name == "Work"
    assert controller.database.load_assignments()[(9, 77)]["profile_id"] == profile_id


def test_a_virtual_profile_cannot_be_launched(tmp_path) -> None:
    controller, _ = _action_controller(tmp_path, [])
    controller.profiles = [Profile(id="virtual-1", directory_name="virtual-1", is_virtual=True)]
    messages: list[str] = []
    controller.statusMessage.connect(messages.append)
    assert not controller.launch_profile("virtual-1")
    assert messages and "cannot be opened" in messages[0]


def test_clicking_a_card_does_not_save_a_guess(tmp_path) -> None:
    from brave_workspace_manager.models import MatchMethod

    window = WindowInfo(window_id=9, pid=77, profile_id="Default", method=MatchMethod.ELIMINATION)
    controller, _ = _action_controller(tmp_path, [window])
    controller.profiles = [Profile(id="Default", directory_name="Default")]
    assert controller.activate_profile("Default")
    assert controller.database.load_assignments() == {}


def test_a_window_can_be_moved_and_unassigned(tmp_path) -> None:
    window = WindowInfo(window_id=9, pid=77, profile_id="Profile 1")
    controller, _ = _action_controller(tmp_path, [window])
    assert controller.assign_window(9, "Default")
    assert controller.database.load_assignments()[(9, 77)]["profile_id"] == "Default"
    assert controller.unassign_window(9)
    assert controller.database.load_assignments() == {}
    assert window.profile_id is None
    assert (9, 77) in controller._detached


def test_the_accessibility_tree_corrects_a_wrong_learned_window(tmp_path) -> None:
    from brave_workspace_manager.models import MatchMethod

    window = WindowInfo(
        window_id=9,
        pid=77,
        title="Dashboard - Brave",
        profile_id="Profile 1",
        method=MatchMethod.LEARNED,
    )
    controller, _ = _action_controller(tmp_path, [window])
    controller.profiles = [
        Profile(id="Default", directory_name="Default", brave_display_name="Alice Doe"),
        Profile(id="Profile 1", directory_name="Profile 1", brave_display_name="Work"),
    ]
    frame = FrameTabs(title="Dashboard - Brave – Alice Doe", titles=["A", "B"])
    controller._aplicar_pestanas([window], [frame])
    assert window.profile_id == "Default"
    assert window.method == MatchMethod.ACCESSIBILITY
    assert controller.database.load_assignments()[(9, 77)]["profile_id"] == "Default"
    assert controller.profiles[0].window_count == 1
    assert controller.profiles[0].tab_count == 2
    assert controller.profiles[1].window_count == 0


def test_a_manual_assignment_beats_the_accessibility_tree(tmp_path) -> None:
    from brave_workspace_manager.models import MatchMethod

    window = WindowInfo(
        window_id=9, pid=77, title="X - Brave", profile_id="Profile 1", method=MatchMethod.MANUAL
    )
    controller, _ = _action_controller(tmp_path, [window])
    controller.profiles = [
        Profile(id="Default", directory_name="Default", brave_display_name="Alice Doe"),
        Profile(id="Profile 1", directory_name="Profile 1", brave_display_name="Work"),
    ]
    controller._aplicar_pestanas([window], [FrameTabs(title="X - Brave – Alice Doe")])
    assert window.profile_id == "Profile 1"


class _FakeSwitch:
    available = True

    def __init__(self, value: bool = False) -> None:
        self.value = value
        self.writes: list[bool] = []

    def get(self) -> bool:
        return self.value

    def set(self, enabled: bool) -> bool:
        self.writes.append(enabled)
        self.value = enabled
        return True


def _pulse_controller(tmp_path, switch: _FakeSwitch) -> AppController:
    window = WindowInfo(window_id=9, pid=77, title="Dashboard - Brave")
    controller = AppController(
        Database(tmp_path / "workspace.db"),
        _ActionBackend([window]),
        _FakeLauncher(),
        user_data_dir=tmp_path / "missing-brave",
        a11y_switch=switch,
    )
    controller.refresh = lambda: None
    controller._programar_lectura_pestanas = lambda: None
    controller.windows = [window]
    return controller


def test_a_window_without_tabs_wakes_up_brave_accessibility(tmp_path) -> None:
    switch = _FakeSwitch(False)
    controller = _pulse_controller(tmp_path, switch)
    controller._on_tabs_read([FrameTabs(title="Dashboard - Brave \u2013 Alice")])
    assert switch.writes == [True]
    controller._finish_a11y_pulse()
    assert switch.writes == [True, False]
    assert controller.tabs_status == ""


def test_the_pulse_is_not_repeated_and_then_warns(tmp_path) -> None:
    switch = _FakeSwitch(False)
    controller = _pulse_controller(tmp_path, switch)
    empty = [FrameTabs(title="Dashboard - Brave")]
    controller._on_tabs_read(empty)
    controller._finish_a11y_pulse()
    controller._on_tabs_read(empty)
    assert switch.writes == [True, False]
    assert "accessibility" in controller.tabs_status.lower()


def test_no_pulse_when_the_tabs_are_visible(tmp_path) -> None:
    switch = _FakeSwitch(False)
    controller = _pulse_controller(tmp_path, switch)
    controller._on_tabs_read([FrameTabs(title="Dashboard - Brave", titles=["A"])])
    assert switch.writes == []


def test_stopping_restores_the_bus_property(tmp_path) -> None:
    switch = _FakeSwitch(False)
    controller = _pulse_controller(tmp_path, switch)
    controller._on_tabs_read([FrameTabs(title="Dashboard - Brave")])
    controller.stop()
    assert switch.value is False
