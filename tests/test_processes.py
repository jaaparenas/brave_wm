"""Pruebas de la inspeccion de procesos de Brave."""

from __future__ import annotations

from pathlib import Path

from brave_workspace_manager import processes


def test_reads_flag_from_normal_arguments() -> None:
    cmdline = ["brave-browser", "--profile-directory=Profile 1", "--no-first-run"]
    assert processes._flag(cmdline, "profile-directory") == "Profile 1"
    assert processes._flag(cmdline, "user-data-dir") is None


def test_reads_flag_from_rewritten_process_title() -> None:
    """Chromium reescribe el titulo de sus procesos secundarios en un solo argumento."""
    cmdline = [
        "/opt/brave.com/brave/brave --type=renderer --lang=en-GB "
        "--enable-sandbox --renderer-client-id=42"
    ]
    assert processes._flag(cmdline, "type") == "renderer"
    assert processes._process_kind(cmdline) == "renderer"


def test_process_kind_defaults_to_browser() -> None:
    assert processes._process_kind(["brave-browser"]) == "browser"


def test_profile_directory_flag() -> None:
    cmdline = ["brave-browser --profile-directory=Profile 7"]
    assert processes._flag(cmdline, "profile-directory") == "Profile 7"


def test_match_profile_directory_matches_only_known_profiles(tmp_path: Path) -> None:
    root = tmp_path / "Brave-Browser"
    known = {"Default", "Profile 1"}
    assert (
        processes.match_profile_directory(str(root / "Profile 1" / "Cookies"), root, known)
        == "Profile 1"
    )
    assert (
        processes.match_profile_directory(str(root / "System Profile" / "Cookies"), root, known)
        is None
    )
    assert processes.match_profile_directory("/otrositio/Default/x", root, known) is None


def test_browser_processes_filters_by_kind() -> None:
    from brave_workspace_manager.models import BrowserProcess

    processes_list = [
        BrowserProcess(pid=1, kind="browser"),
        BrowserProcess(pid=2, kind="renderer"),
        BrowserProcess(pid=3, kind="browser"),
    ]
    assert [p.pid for p in processes.browser_processes(processes_list)] == [1, 3]
