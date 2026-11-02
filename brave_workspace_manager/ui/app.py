"""Arranque de la aplicacion de escritorio."""

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
from ..x11 import create_backend
from ..x11.grab import ShortcutGrabber
from . import icons
from .main_window import MainWindow
from .theme import STYLESHEET


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="brave-workspace-manager", description=APP_SUMMARY)
    parser.add_argument("--version", action="version", version=f"{APP_NAME} {APP_VERSION}")
    parser.add_argument(
        "--minimized", action="store_true", help="inicia oculto en la bandeja del sistema"
    )
    parser.add_argument(
        "--user-data-dir",
        default=None,
        help="directorio de datos de Brave (por defecto, el habitual)",
    )
    return parser


def _lock_owner_pid(path: Path) -> int:
    """Lee el PID que escribio QLockFile en la primera linea."""
    try:
        first = path.read_text(encoding="utf-8").splitlines()[0].strip()
    except (OSError, IndexError):
        return 0
    return int(first) if first.isdigit() else 0


def _recover_stale_lock(lock: QLockFile, path: Path) -> bool:
    """Libera el bloqueo si el proceso que lo creo ya no existe.

    QLockFile solo considera un bloqueo rancio por antiguedad, y aqui la
    antiguedad esta desactivada a proposito: si la aplicacion termina de
    forma abrupta, el fichero se queda y bloquearia todos los arranques
    siguientes. Comprobando el PID se recupera sin esperar.
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

    lock_path = data_dir() / "instance.lock"
    lock = QLockFile(str(lock_path))
    lock.setStaleLockTime(0)
    if not lock.tryLock(100) and not _recover_stale_lock(lock, lock_path):
        QMessageBox.information(
            None,
            APP_NAME,
            "Brave Workspace Manager ya se esta ejecutando.\n"
            "Revisa la bandeja del sistema para abrirlo.",
        )
        return 1

    database = Database(database_path())
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

    if args.minimized:
        window.hide()
    else:
        window.show()

    try:
        return app.exec()
    finally:
        database.close()
