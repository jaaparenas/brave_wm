"""Generates the documentation screenshots with synthetic data.

Nothing is read from the real user profile: a fake Brave data directory is
built in a temporary folder and the main window is drawn on top of it.

    python tools/screenshot.py
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QCoreApplication, QEvent, QRect
from PySide6.QtWidgets import QApplication

from brave_workspace_manager import i18n
from brave_workspace_manager.core.controller import AppController
from brave_workspace_manager.core.launcher import ProfileLauncher
from brave_workspace_manager.database import Database
from brave_workspace_manager.models import WindowInfo
from brave_workspace_manager.tabs import FrameTabs
from brave_workspace_manager.ui import icons
from brave_workspace_manager.ui.main_window import MainWindow
from brave_workspace_manager.ui.theme import STYLESHEET

TARGET = ROOT / "docs" / "images"

PROFILES = {
    "Default": "Work",
    "Profile 1": "Personal",
    "Profile 2": "Testing",
    "Profile 3": "Research",
    "Profile 4": "Design",
    "Profile 5": "Finance",
    "Profile 6": "Reading",
    "Profile 7": "Coding",
}

WINDOWS = [
    WindowInfo(
        window_id=0x400001,
        pid=100,
        title="Work · Dashboard",
        wm_class="brave-browser",
        is_active=True,
        is_maximized=True,
    ),
    WindowInfo(
        window_id=0x400002,
        pid=100,
        title="Personal · Photos",
        wm_class="brave-browser",
    ),
    WindowInfo(
        window_id=0x400003,
        pid=100,
        title="Coding · Pull requests",
        wm_class="brave-browser",
        is_minimized=True,
    ),
    WindowInfo(
        window_id=0x400004,
        pid=100,
        title="Example documentation",
        wm_class="brave-browser",
    ),
]

FRAMES = [
    FrameTabs(title="Work · Dashboard", titles=["Dashboard", "Calendar", "Team notes"], active=0),
    FrameTabs(title="Personal · Photos", titles=["Photos", "Mail"], active=0),
    FrameTabs(
        title="Coding · Pull requests",
        titles=["Pull requests", "CI", "Docs", "Issues", "Board"],
        active=0,
    ),
    FrameTabs(title="Example documentation", titles=["Example documentation"], active=0),
]


class FakeBackend:
    """Fake window backend for the screenshots."""

    name = "demo"

    def is_available(self) -> bool:
        return True

    def list_windows(self) -> list[WindowInfo]:
        return list(WINDOWS)

    def activate(self, window_id: int) -> bool:
        return True

    def minimize(self, window_id: int) -> bool:
        return True

    def restore(self, window_id: int) -> bool:
        return True

    def maximize(self, window_id: int) -> bool:
        return True

    def unmaximize(self, window_id: int) -> bool:
        return True

    def close_window(self, window_id: int) -> bool:
        return True

    def active_window(self) -> int | None:
        return WINDOWS[0].window_id


class FakeReader:
    """Fake tab reader for the screenshots."""

    motivo = ""
    disponible = True

    def read(self) -> list[FrameTabs]:
        return list(FRAMES)


def fake_brave_dir(base: Path) -> Path:
    root = base / "Brave-Browser"
    root.mkdir()
    info_cache = {
        key: {"name": value, "gaia_name": "", "active_time": 1700000000.0}
        for key, value in PROFILES.items()
    }
    (root / "Local State").write_text(
        json.dumps(
            {
                "profile": {
                    "last_used": "Default",
                    "last_active_profiles": ["Default", "Profile 1"],
                    "info_cache": info_cache,
                }
            }
        ),
        encoding="utf-8",
    )
    for key in PROFILES:
        folder = root / key
        folder.mkdir()
        (folder / "Preferences").write_text("{}", encoding="utf-8")
    return root


def settle(app: QApplication) -> None:
    app.processEvents()
    QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
    app.processEvents()


def main() -> int:
    TARGET.mkdir(parents=True, exist_ok=True)
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setStyleSheet(STYLESHEET)
    app.setWindowIcon(icons.app_pixmap())

    with tempfile.TemporaryDirectory() as temporary:
        base = Path(temporary)
        root = fake_brave_dir(base)
        database = Database(base / "workspace.db")
        database.set_setting("language", "en")
        i18n.set_language("en")
        database.set_setting("hotkeys_enabled", "0")
        controller = AppController(
            database,
            FakeBackend(),
            ProfileLauncher("/usr/bin/brave-browser", root),
            user_data_dir=root,
            tab_reader=FakeReader(),
        )
        controller.set_read_tabs(False)
        controller.refresh()
        controller.set_read_tabs(True)
        controller._on_tabs_read(FakeReader().read())

        window = MainWindow(controller, database)
        window.resize(1280, 800)
        window.show()
        controller.select("Default")
        settle(app)
        window.grab().save(str(TARGET / "main-window.png"))

        gallery = window._gallery
        card = gallery.unassigned_card
        top = max(0, card.y() - 210)
        gallery.grab(QRect(0, top, gallery.width(), card.y() + card.height() - top)).save(
            str(TARGET / "unassigned-card.png")
        )

        window._language_combo.setCurrentIndex(window._language_combo.findData("es"))
        settle(app)
        window.grab().save(str(TARGET / "main-window-es.png"))
        i18n.set_language("en")

        controller.stop()
        database.close()

    print(f"Screenshots saved in {TARGET}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
