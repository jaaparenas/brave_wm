"""Integration with the autostart of the desktop session."""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

from ..config import APP_ID, APP_NAME, XDG_CONFIG_HOME

DESKTOP_ENTRY = """[Desktop Entry]
Type=Application
Name={name}
Comment=Native Brave profile manager
Exec={exec}
Icon={icon}
Terminal=false
Categories=Utility;
X-GNOME-Autostart-enabled=true
X-GNOME-Autostart-Delay=5
"""


def desktop_file_path() -> Path:
    return XDG_CONFIG_HOME / "autostart" / f"{APP_ID}.desktop"


def is_enabled() -> bool:
    return desktop_file_path().is_file()


def enable(command: str | None = None) -> bool:
    """Starts the app hidden in the tray when the session begins."""
    path = desktop_file_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    exec_line = command or python_command()
    if "--minimized" not in exec_line:
        exec_line = f"{exec_line} --minimized"
    path.write_text(
        DESKTOP_ENTRY.format(name=APP_NAME, exec=exec_line, icon=APP_ID),
        encoding="utf-8",
    )
    return True


def disable() -> bool:
    path = desktop_file_path()
    try:
        path.unlink()
    except FileNotFoundError:
        return False
    except OSError:
        return False
    return True


def python_command() -> str:
    """Command that starts the application when the session begins."""
    executable = os.environ.get("BRAVE_WORKSPACE_MANAGER_CMD")
    if executable:
        return executable
    launcher = shutil.which(APP_ID)
    if launcher:
        return launcher
    return f"{sys.executable} -m brave_workspace_manager"
