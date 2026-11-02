"""Genera las capturas de la documentacion con datos sinteticos.

No lee nada del perfil real del usuario: construye un directorio de datos de
Brave simulado en un temporal y dibuja la ventana principal sobre el.

    python tools/screenshot.py
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QCoreApplication, QEvent
from PySide6.QtWidgets import QApplication

from brave_workspace_manager.core.controller import AppController
from brave_workspace_manager.core.launcher import ProfileLauncher
from brave_workspace_manager.database import Database
from brave_workspace_manager.models import WindowInfo
from brave_workspace_manager.ui import icons
from brave_workspace_manager.ui.main_window import MainWindow
from brave_workspace_manager.ui.theme import STYLESHEET

DESTINO = RAIZ / "docs" / "images"

PERFILES = {
    "Default": "Trabajo",
    "Profile 1": "Personal",
    "Profile 2": "Pruebas",
    "Profile 3": "Investigación",
}

VENTANAS = [
    WindowInfo(
        window_id=0x400001,
        pid=100,
        title="Work · Panel de control",
        wm_class="brave-browser",
        is_active=True,
    ),
    WindowInfo(
        window_id=0x400002,
        pid=100,
        title="Documentación de ejemplo",
        wm_class="brave-browser",
    ),
    WindowInfo(
        window_id=0x400003,
        pid=100,
        title="Trabajo · Cuadro de mando",
        wm_class="brave-browser",
        is_minimized=True,
    ),
]


class BackendFalso:
    """Backend de ventanas simulado para las capturas."""

    name = "demo"

    def is_available(self) -> bool:
        return True

    def list_windows(self) -> list[WindowInfo]:
        return list(VENTANAS)

    def activate(self, window_id: int) -> bool:
        return True

    def minimize(self, window_id: int) -> bool:
        return True

    def restore(self, window_id: int) -> bool:
        return True

    def active_window(self) -> int | None:
        return VENTANAS[0].window_id


def directorio_falso(base: Path) -> Path:
    raiz = base / "Brave-Browser"
    raiz.mkdir()
    info_cache = {
        clave: {"name": valor, "gaia_name": "", "active_time": 1700000000.0}
        for clave, valor in PERFILES.items()
    }
    (raiz / "Local State").write_text(
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
    for clave in PERFILES:
        carpeta = raiz / clave
        carpeta.mkdir()
        (carpeta / "Preferences").write_text("{}", encoding="utf-8")
    return raiz


def main() -> int:
    DESTINO.mkdir(parents=True, exist_ok=True)
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setStyleSheet(STYLESHEET)
    app.setWindowIcon(icons.app_pixmap())

    with tempfile.TemporaryDirectory() as temporal:
        base = Path(temporal)
        raiz = directorio_falso(base)
        database = Database(base / "workspace.db")
        controller = AppController(
            database,
            BackendFalso(),
            ProfileLauncher("/usr/bin/brave-browser", raiz),
            user_data_dir=raiz,
        )
        controller.refresh()

        ventana = MainWindow(controller, database)
        ventana.resize(1220, 760)
        ventana.show()
        app.processEvents()
        QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
        app.processEvents()
        ventana.grab().save(str(DESTINO / "ventana-principal.png"))

        ventana._admin_button.setChecked(True)
        app.processEvents()
        QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
        app.processEvents()
        ventana.grab().save(str(DESTINO / "panel-admin.png"))
        database.close()

    print(f"Capturas guardadas en {DESTINO}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
