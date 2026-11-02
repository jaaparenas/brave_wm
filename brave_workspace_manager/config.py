"""Paths, desktop environment detection and binary lookup."""

from __future__ import annotations

import os
import shutil
from pathlib import Path

APP_ID = "brave-workspace-manager"
APP_NAME = "Brave Workspace Manager"
APP_VERSION = "1.1.0"
APP_SUMMARY = "Native Brave profile manager for Linux Mint / Cinnamon"

DEFAULT_BRAVE_DIR = Path.home() / ".config" / "BraveSoftware" / "Brave-Browser"

_BRAVE_BINARIES = (
    "brave-browser",
    "brave-browser-stable",
    "brave",
    "brave-browser-beta",
    "brave-browser-nightly",
    "brave-browser-dev",
)

_BRAVE_PATHS = (
    "/usr/bin/brave-browser",
    "/usr/bin/brave-browser-stable",
    "/opt/brave.com/brave/brave",
    "/usr/bin/brave",
    "/snap/bin/brave",
    "/var/lib/flatpak/exports/bin/com.brave.Browser",
)


def _xdg(variable: str, fallback: str) -> Path:
    value = os.environ.get(variable)
    if not value:
        return Path.home() / fallback
    return Path(value).expanduser()


XDG_CONFIG_HOME = _xdg("XDG_CONFIG_HOME", ".config")
XDG_DATA_HOME = _xdg("XDG_DATA_HOME", ".local/share")
XDG_STATE_HOME = _xdg("XDG_STATE_HOME", ".local/state")


def brave_user_data_dir() -> Path:
    """Root data directory of Brave (holds Local State and the profiles)."""
    override = os.environ.get("BRAVE_USER_DATA_DIR")
    if override:
        return Path(override).expanduser()
    return DEFAULT_BRAVE_DIR


def config_dir() -> Path:
    return XDG_CONFIG_HOME / APP_ID


def data_dir() -> Path:
    return XDG_DATA_HOME / APP_ID


def state_dir() -> Path:
    return XDG_STATE_HOME / APP_ID


def database_path() -> Path:
    return data_dir() / "workspace.db"


def log_path() -> Path:
    return state_dir() / "brave-workspace-manager.log"


def find_brave_binary() -> str | None:
    """Absolute path of the Brave executable, or None when it is not installed."""
    for name in _BRAVE_BINARIES:
        found = shutil.which(name)
        if found:
            return found
    for candidate in _BRAVE_PATHS:
        if Path(candidate).exists():
            return candidate
    return None


def session_type() -> str:
    return (os.environ.get("XDG_SESSION_TYPE") or "x11").lower()


def is_wayland() -> bool:
    return session_type() == "wayland"


def desktop_environment() -> str:
    return (os.environ.get("XDG_CURRENT_DESKTOP") or "").lower()


def ensure_dirs() -> None:
    for path in (config_dir(), data_dir(), state_dir()):
        path.mkdir(parents=True, exist_ok=True)
