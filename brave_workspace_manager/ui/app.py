"""Entry point of the desktop application."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from PySide6.QtCore import QLockFile
from PySide6.QtWidgets import QApplication, QMessageBox

from ..config import (
    APP_NAME,
    APP_SUMMARY,
    APP_VERSION,
    brave_user_data_dir,
    data_dir,
    database_path,
    ensure_dirs,
    find_brave_binary,
)
from ..core.controller import AppController
from ..core.launcher import ProfileLauncher
from ..database import Database
from ..i18n import detect_system_language, set_language, tr
from ..x11 import create_backend
from ..x11.grab import ShortcutGrabber
from . import icons
from .main_window import MainWindow
from .theme import STYLESHEET


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="brave-workspace-manager", description=APP_SUMMARY)
    parser.add_argument("--version", action="version", version=f"{APP_NAME} {APP_VERSION}")
    parser.add_argument(
        "--minimized",
        action="store_true",
        help="start hidden in the system tray",
    )
    parser.add_argument(
        "--user-data-dir",
        default=None,
        help="Brave data directory (defaults to the usual one)",
    )
    parser.add_argument(
        "--language",
        default=None,
        help="interface language, for example 'en' or 'es'",
    )
    return parser


def _lock_owner_pid(path: Path) -> int:
    """Reads the PID that QLockFile wrote in the first line."""
    try:
        first = path.read_text(encoding="utf-8").splitlines()[0].strip()
    except (OSError, IndexError):
        return 0
    return int(first) if first.isdigit() else 0


def _recover_stale_lock(lock: QLockFile, path: Path) -> bool:
    """Releases the lock when the process that created it is gone.

    QLockFile only considers a lock stale because of its age, and that age
    limit is disabled on purpose here: if the application ends abruptly the
    file stays behind and would block every later start. Checking the PID
    recovers the lock without waiting.
    """
    pid = _lock_owner_pid(path)
    if pid <= 0 or Path(f"/proc/{pid}").exists():
        return False
    try:
        path.unlink()
    except OSError:
        return False
    return lock.tryLock(100)


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    ensure_dirs()

    qt_argv = [sys.argv[0], *(argv if argv is not None else sys.argv[1:])]
    app = QApplication(qt_argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationDisplayName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)
    app.setWindowIcon(icons.app_pixmap())
    app.setStyle("Fusion")
    app.setStyleSheet(STYLESHEET)

    database = Database(database_path())
    stored_language = database.get_setting("language")
    set_language(args.language or stored_language or detect_system_language())

    lock_path = data_dir() / "instance.lock"
    lock = QLockFile(str(lock_path))
    lock.setStaleLockTime(0)
    if not lock.tryLock(100) and not _recover_stale_lock(lock, lock_path):
        QMessageBox.information(None, APP_NAME, tr("status.already_running"))
        return 1

    backend = create_backend()
    launcher = ProfileLauncher(find_brave_binary(), brave_user_data_dir())
    controller = AppController(
        database,
        backend,
        launcher,
        user_data_dir=args.user_data_dir or brave_user_data_dir(),
    )

    window = MainWindow(controller, database)
    grabber = ShortcutGrabber(window.relay.triggered.emit)
    window.grabber = grabber
    window.start()

    controller.start()

    if args.minimized and window.has_tray:
        window.hide()
    else:
        window.show()

    try:
        return app.exec()
    finally:
        database.close()
