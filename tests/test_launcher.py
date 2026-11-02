"""Pruebas del lanzador de perfiles."""

from __future__ import annotations

import subprocess
from pathlib import Path

from brave_workspace_manager.core.launcher import ProfileLauncher


class _Recorder:
    def __init__(self) -> None:
        self.commands: list[list[str]] = []

    def __call__(self, args, **kwargs):
        self.commands.append(args)
        return object()


def test_launch_uses_the_native_profile_directory(monkeypatch, tmp_path: Path) -> None:
    recorder = _Recorder()
    monkeypatch.setattr(subprocess, "Popen", recorder)
    launcher = ProfileLauncher("/usr/bin/brave-browser", tmp_path)
    assert launcher.launch("Profile 1") is True
    assert recorder.commands[0][0] == "/usr/bin/brave-browser"
    assert recorder.commands[0][1] == "--profile-directory=Profile 1"


def test_launch_is_disabled_without_binary(monkeypatch, tmp_path: Path) -> None:
    launcher = ProfileLauncher(None, tmp_path)
    assert launcher.available is False
    assert launcher.launch("Default") is False


def test_open_profile_manager_uses_brave_url(monkeypatch, tmp_path: Path) -> None:
    recorder = _Recorder()
    monkeypatch.setattr(subprocess, "Popen", recorder)
    launcher = ProfileLauncher("/usr/bin/brave-browser", tmp_path)
    assert launcher.open_profile_manager() is True
    assert recorder.commands[0][1].startswith("brave://")


def test_spawn_failure_is_reported(monkeypatch, tmp_path: Path) -> None:
    def explode(args, **kwargs):
        raise OSError("no existe")

    monkeypatch.setattr(subprocess, "Popen", explode)
    launcher = ProfileLauncher("/usr/bin/brave-browser", tmp_path)
    assert launcher.launch("Default") is False
