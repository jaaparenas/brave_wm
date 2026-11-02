"""Tests of the session autostart entry."""

from __future__ import annotations

from brave_workspace_manager.core import autostart


def _use(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(autostart, "XDG_CONFIG_HOME", tmp_path)


def test_enable_starts_hidden_in_the_tray(tmp_path, monkeypatch) -> None:
    _use(tmp_path, monkeypatch)
    assert autostart.enable("/home/u/.local/bin/brave-workspace-manager")
    text = autostart.desktop_file_path().read_text(encoding="utf-8")
    assert "Exec=/home/u/.local/bin/brave-workspace-manager --minimized" in text
    assert "X-GNOME-Autostart-enabled=true" in text
    assert autostart.is_enabled()


def test_minimized_is_not_added_twice(tmp_path, monkeypatch) -> None:
    _use(tmp_path, monkeypatch)
    autostart.enable("bwm --minimized")
    assert "Exec=bwm --minimized\n" in autostart.desktop_file_path().read_text(encoding="utf-8")


def test_disable_removes_the_entry(tmp_path, monkeypatch) -> None:
    _use(tmp_path, monkeypatch)
    autostart.enable("bwm")
    assert autostart.disable()
    assert not autostart.is_enabled()
    assert not autostart.disable()


def test_the_command_prefers_the_installed_launcher(monkeypatch) -> None:
    monkeypatch.delenv("BRAVE_WORKSPACE_MANAGER_CMD", raising=False)
    monkeypatch.setattr(autostart.shutil, "which", lambda name: f"/opt/bin/{name}")
    assert autostart.python_command() == "/opt/bin/brave-workspace-manager"


def test_the_command_falls_back_to_the_interpreter(monkeypatch) -> None:
    monkeypatch.delenv("BRAVE_WORKSPACE_MANAGER_CMD", raising=False)
    monkeypatch.setattr(autostart.shutil, "which", lambda name: None)
    assert autostart.python_command().endswith("-m brave_workspace_manager")
