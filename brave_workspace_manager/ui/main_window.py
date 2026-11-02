"""Ventana principal: barra de perfiles, ventanas y administracion."""

from __future__ import annotations

from PySide6.QtCore import QObject, Qt, Signal
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QApplication,
    QColorDialog,
    QDialog,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QMainWindow,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSplitter,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from ..config import APP_NAME, APP_VERSION, desktop_environment, session_type
from ..core import autostart
from ..core.controller import AppController
from ..database import Database
from ..x11.grab import ShortcutGrabber
from . import icons
from .admin_panel import DEFAULT_SHORTCUTS, SHORTCUT_ACTIONS, AdminPanel
from .profile_tab import ProfileTab
from .tray import TrayIcon
from .window_panel import WindowPanel


class ShortcutRelay(QObject):
    """Puente seguro entre el hilo que captura las teclas y la interfaz."""

    triggered = Signal(str)


class HelpDialog(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"Ayuda · {APP_NAME}")
        self.resize(680, 520)
        layout = QVBoxLayout(self)
        browser = QTextBrowser()
        browser.setOpenExternalLinks(True)
        browser.setHtml(
            f"""
            <h2>{APP_NAME} {APP_VERSION}</h2>
            <p>Administra los perfiles nativos de Brave desde una sola ventana: consulta
            cuales estan abiertos, cambia de perfil con un clic o con un atajo y
            personaliza nombre, color, icono y orden.</p>
            <h3>Como se identifica cada ventana</h3>
            <p>Chromium ejecuta todas las ventanas de todos los perfiles de un mismo
            directorio de datos dentro de un unico proceso, y no publica ninguna
            propiedad X11 que indique el perfil de origen. Por eso la aplicacion
            <b>aprende</b> la relacion: recuerda las ventanas que abriste, deduce el
            perfil cuando solo hay uno activo y permite asignar a mano las restantes.</p>
            <h3>Atajos</h3>
            <ul>
              <li><b>Ctrl+Alt+1…9</b>: activar el perfil de la posicion indicada.</li>
              <li><b>Ctrl+Alt+Tab</b> / <b>Ctrl+Alt+Shift+Tab</b>: perfil siguiente o anterior.</li>
              <li><b>Ctrl+Alt+B</b>: mostrar u ocultar el panel de administracion.</li>
            </ul>
            <h3>Privacidad</h3>
            <p>La aplicacion no lee cookies, contrasenas ni historial de Brave, no
            modifica <i>Local State</i> ni las bases de datos internas de los perfiles,
            no intercepta trafico y no comparte directorios entre perfiles. Solo lee
            el nombre visible de los perfiles y lista los procesos y las ventanas.</p>
            """
        )
        layout.addWidget(browser)
        close = QPushButton("Cerrar")
        close.clicked.connect(self.accept)
        layout.addWidget(close, 0, Qt.AlignRight)


class MainWindow(QMainWindow):
    """Interfaz principal de la aplicacion."""

    def __init__(
        self,
        controller: AppController,
        database: Database,
        grabber: ShortcutGrabber | None = None,
    ) -> None:
        super().__init__()
        self.controller = controller
        self.database = database
        self.grabber = grabber
        self._tabs: dict[str, ProfileTab] = {}
        self._activate_on_click = True
        self._tray: TrayIcon | None = None
        self._tray_enabled = False

        self.setWindowTitle(APP_NAME)
        self.setWindowIcon(icons.app_pixmap())
        self.resize(1220, 760)
        self.setMinimumSize(940, 560)

        self.relay = ShortcutRelay()
        self.relay.triggered.connect(self._on_shortcut)

        self._build_ui()
        self._connect_controller()
        self._load_settings()
        self._install_local_shortcuts()
        self._rebuild_profiles()

    # ------------------------------------------------------------- construccion

    def _build_ui(self) -> None:
        central = QWidget()
        root = QVBoxLayout(central)
        root.setContentsMargins(14, 12, 14, 8)
        root.setSpacing(12)

        self._splitter = QSplitter(Qt.Horizontal)
        self._window_panel = WindowPanel()
        self._window_panel.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self._admin_panel = AdminPanel()
        self._admin_panel.setVisible(False)
        self._splitter.addWidget(self._window_panel)
        self._splitter.addWidget(self._admin_panel)
        self._splitter.setStretchFactor(0, 3)
        self._splitter.setStretchFactor(1, 2)

        root.addLayout(self._build_header())
        root.addWidget(self._build_profile_bar(), 0)
        root.addWidget(self._splitter, 1)

        self.setCentralWidget(central)

        self._status_label = QLabel()
        self._status_left = QLabel()
        self.statusBar().addWidget(self._status_left, 1)
        self.statusBar().addPermanentWidget(self._status_label)

    def _build_header(self) -> QHBoxLayout:
        header = QHBoxLayout()
        header.setSpacing(10)

        titles = QVBoxLayout()
        titles.setSpacing(2)
        title = QLabel(APP_NAME)
        title.setObjectName("HeaderTitle")
        titles.addWidget(title)
        self._subtitle = QLabel("Descubriendo perfiles...")
        self._subtitle.setObjectName("HeaderSubtitle")
        titles.addWidget(self._subtitle)
        header.addLayout(titles)
        header.addStretch(1)

        self._refresh_button = QPushButton("Actualizar")
        self._refresh_button.clicked.connect(self.controller.refresh)
        header.addWidget(self._refresh_button)

        self._admin_button = QPushButton("Administrador")
        self._admin_button.setCheckable(True)
        self._admin_button.setToolTip("Ctrl+Alt+B")
        self._admin_button.toggled.connect(self._admin_panel.setVisible)
        header.addWidget(self._admin_button)

        self._tray_button = QPushButton("Bandeja")
        self._tray_button.setCheckable(True)
        self._tray_button.toggled.connect(self._set_tray_enabled)
        header.addWidget(self._tray_button)

        help_button = QPushButton("Ayuda")
        help_button.clicked.connect(self._show_help)
        header.addWidget(help_button)
        return header

    def _build_profile_bar(self) -> QScrollArea:
        self._profile_container = QWidget()
        self._profile_layout = QHBoxLayout(self._profile_container)
        self._profile_layout.setContentsMargins(0, 0, 0, 0)
        self._profile_layout.setSpacing(10)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setWidget(self._profile_container)
        scroll.setFixedHeight(ProfileTab.HEIGHT + 16)
        return scroll

    # ------------------------------------------------------------- senales

    def _connect_controller(self) -> None:
        self.controller.profilesChanged.connect(self._rebuild_profiles)
        self.controller.windowsChanged.connect(self._refresh_windows)
        self.controller.statusMessage.connect(self._show_status)
        self.controller.selectionChanged.connect(self._on_selection_changed)

        panel = self._admin_panel
        panel.renameRequested.connect(self.controller.rename_profile)
        panel.colorRequested.connect(self._on_color_requested)
        panel.iconRequested.connect(
            lambda profile_id, icon: self.controller.update_profile(profile_id, icon=icon)
        )
        panel.favoriteToggled.connect(
            lambda profile_id, state: self.controller.update_profile(profile_id, is_favorite=state)
        )
        panel.moveRequested.connect(self.controller.move_profile)
        panel.resetRequested.connect(self.controller.reset_profile)
        panel.openProfileRequested.connect(self.controller.launch_profile)
        panel.manageProfilesRequested.connect(self.controller.open_profiles_manager)
        panel.settingChanged.connect(self._on_setting_changed)
        panel.shortcutChanged.connect(self._on_shortcut_changed)
        panel.shortcutResetRequested.connect(self._reset_shortcuts)
        panel.selectionChanged.connect(self.controller.select)

        self._window_panel.windowActivated.connect(self._on_window_activated)
        self._window_panel.windowToggled.connect(self.controller.toggle_window)
        self._window_panel.windowAssigned.connect(self.controller.assign_window)
        self._window_panel.adoptRequested.connect(self.controller.adopt_active_window)
        self._window_panel.openProfileRequested.connect(self.controller.launch_profile)

    def _load_settings(self) -> None:
        settings = {
            "poll_interval": self.database.get_setting("poll_interval", "2000"),
            "activate_on_click": self.database.get_setting("activate_on_click", "1"),
            "hotkeys_enabled": self.database.get_setting("hotkeys_enabled", "1"),
            "tray_enabled": self.database.get_setting("tray_enabled", "0"),
            "autostart": self.database.get_setting("autostart", "0"),
        }
        self._activate_on_click = settings["activate_on_click"] == "1"
        self._admin_panel.set_settings(settings)
        self.controller.set_poll_interval(int(settings["poll_interval"]))
        self._tray_button.setChecked(settings["tray_enabled"] == "1")
        self._admin_panel.set_shortcuts(self._shortcut_bindings())
        if settings["hotkeys_enabled"] == "1":
            self._apply_shortcuts()

    def _shortcut_bindings(self) -> dict[str, str]:
        bindings = dict(DEFAULT_SHORTCUTS)
        for action, _ in SHORTCUT_ACTIONS:
            stored = self.database.get_setting(f"shortcut.{action}")
            if stored:
                bindings[action] = stored
        return bindings

    def _install_local_shortcuts(self) -> None:
        """Atajos que funcionan cuando la ventana tiene el foco."""
        for action, sequence in self._shortcut_bindings().items():
            shortcut = QShortcut(QKeySequence(sequence), self)
            shortcut.activated.connect(lambda a=action: self._on_shortcut(a))

    def start(self) -> None:
        """Arranca las capturas globales de teclado, que necesitan el grabber."""
        self._install_local_shortcuts()
        if self.database.get_setting("hotkeys_enabled", "1") == "1":
            self._apply_shortcuts()

    # ------------------------------------------------------------- renderizado

    def _rebuild_profiles(self) -> None:
        while self._profile_layout.count():
            item = self._profile_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        self._tabs.clear()

        for profile in self.controller.profiles:
            tab = ProfileTab(profile)
            tab.activated.connect(self._on_profile_clicked)
            tab.doubleClicked.connect(self.controller.launch_profile)
            tab.contextRequested.connect(self._show_profile_menu)
            self._profile_layout.addWidget(tab)
            self._tabs[profile.id] = tab
        self._profile_layout.addStretch(1)

        open_count = sum(1 for p in self.controller.profiles if p.is_open)
        window_count = len(self.controller.windows)
        self._subtitle.setText(
            f"{len(self.controller.profiles)} perfiles · {open_count} abiertos · "
            f"{window_count} ventanas de Brave detectadas"
        )
        self._admin_panel.set_profiles(self.controller.profiles)
        if self._tray is not None:
            self._tray.set_profiles(self.controller.profiles)
        self._refresh_windows()

    def _refresh_windows(self) -> None:
        selected = self.controller.selected_profile_id
        profile = self.controller.profile(selected) if selected else None
        if profile is None and self.controller.profiles:
            profile = self.controller.profiles[0]
            self.controller.select(profile.id)
        self._window_panel.set_profile(profile)
        self._window_panel.set_windows(
            self.controller.windows_for(profile.id if profile else None), self.controller.profiles
        )
        self._window_panel.set_unassigned(
            self.controller.unassigned_windows(), self.controller.profiles
        )
        self._status_label.setText(
            f"Backend: {self.controller.backend.name} · Sesion: {session_type()} "
            f"· Escritorio: {desktop_environment() or 'desconocido'}"
        )
        for profile_id, tab in self._tabs.items():
            current = self.controller.profile(profile_id)
            if current is not None:
                tab.update_profile(current)

    def _on_selection_changed(self, profile_id: str) -> None:
        self._admin_panel.select_profile(profile_id)
        self._refresh_windows()

    # ------------------------------------------------------------- acciones

    def _on_profile_clicked(self, profile_id: str) -> None:
        self.controller.select(profile_id)
        if self._activate_on_click:
            self.controller.activate_profile(profile_id)

    def _on_window_activated(self, window_id: int) -> None:
        if self.controller.backend.activate(window_id):
            self._show_status("Ventana activada.")
            self.controller.refresh()
        else:
            self._show_status("No se pudo activar la ventana.")

    def _on_color_requested(self, profile_id: str, color: str) -> None:
        self.controller.update_profile(profile_id, color=color)

    def _on_setting_changed(self, key: str, value: str) -> None:
        self.database.set_setting(key, value)
        if key == "poll_interval":
            self.controller.set_poll_interval(int(value))
        elif key == "activate_on_click":
            self._activate_on_click = value == "1"
        elif key == "hotkeys_enabled":
            if value == "1":
                self._apply_shortcuts()
            elif self.grabber is not None:
                self.grabber.stop()
        elif key == "tray_enabled":
            self._tray_button.setChecked(value == "1")
        elif key == "autostart":
            if value == "1":
                autostart.enable(autostart.python_command())
            else:
                autostart.disable()

    def _on_shortcut_changed(self, action: str, sequence: str) -> None:
        self.database.set_setting(f"shortcut.{action}", sequence)
        self._apply_shortcuts()
        self._install_local_shortcuts()

    def _reset_shortcuts(self) -> None:
        for action, _ in SHORTCUT_ACTIONS:
            self.database.set_setting(f"shortcut.{action}", DEFAULT_SHORTCUTS[action])
        self._admin_panel.set_shortcuts(self._shortcut_bindings())
        self._apply_shortcuts()
        self._install_local_shortcuts()

    def _apply_shortcuts(self) -> None:
        if self.grabber is None:
            return
        failures = self.grabber.start(self._shortcut_bindings())
        if failures:
            detail = ", ".join(
                f"{action}: {reason}" for action, reason in failures.items() if action != "_last"
            )
            self._show_status(f"Atajo en conflicto: {detail}" if detail else "Atajo en conflicto.")
        else:
            self._show_status("Atajos globales registrados.")

    def _on_shortcut(self, action: str) -> None:
        profiles = self.controller.profiles
        if action.startswith("profile-"):
            try:
                position = int(action.split("-", 1)[1]) - 1
            except ValueError:
                return
            if 0 <= position < len(profiles):
                self.controller.select(profiles[position].id)
                self.controller.activate_profile(profiles[position].id)
        elif action == "next-profile":
            self._cycle_profile(1)
        elif action == "prev-profile":
            self._cycle_profile(-1)
        elif action == "toggle-admin":
            self._admin_button.setChecked(not self._admin_button.isChecked())

    def _cycle_profile(self, delta: int) -> None:
        profiles = self.controller.profiles
        if not profiles:
            return
        current = self.controller.selected_profile_id
        index = next((i for i, p in enumerate(profiles) if p.id == current), 0)
        target = profiles[(index + delta) % len(profiles)]
        self.controller.select(target.id)
        self.controller.activate_profile(target.id)

    def _show_profile_menu(self, profile_id: str, position) -> None:
        from PySide6.QtWidgets import QMenu

        profile = self.controller.profile(profile_id)
        if profile is None:
            return
        menu = QMenu(self)
        activate = menu.addAction("Activar")
        activate.triggered.connect(lambda: self.controller.activate_profile(profile_id))
        open_action = menu.addAction("Abrir perfil")
        open_action.triggered.connect(lambda: self.controller.launch_profile(profile_id))
        adopt = menu.addAction("Tomar la ventana activa")
        adopt.triggered.connect(lambda: self.controller.adopt_active_window(profile_id))

        menu.addSeparator()
        rename = menu.addAction("Renombrar...")
        rename.triggered.connect(lambda: self._rename_dialog(profile_id))
        color = menu.addAction("Cambiar color...")
        color.triggered.connect(lambda: self._color_dialog(profile_id))

        icon_menu = menu.addMenu("Icono")
        for name in icons.GLYPH_NAMES:
            action = icon_menu.addAction(icons.glyph_pixmap(name, "#e7eaf0", 16), name)
            action.triggered.connect(
                lambda _checked=False, value=name: self.controller.update_profile(
                    profile_id, icon=value
                )
            )

        favorite = menu.addAction(
            "Marcar como favorito" if not profile.is_favorite else "Quitar de favoritos"
        )
        favorite.triggered.connect(
            lambda: self.controller.update_profile(profile_id, is_favorite=not profile.is_favorite)
        )

        menu.addSeparator()
        up = menu.addAction("Subir")
        up.triggered.connect(lambda: self.controller.move_profile(profile_id, -1))
        down = menu.addAction("Bajar")
        down.triggered.connect(lambda: self.controller.move_profile(profile_id, 1))
        reset = menu.addAction("Restablecer")
        reset.triggered.connect(lambda: self.controller.reset_profile(profile_id))
        menu.exec(position)

    def _rename_dialog(self, profile_id: str) -> None:
        profile = self.controller.profile(profile_id)
        if profile is None:
            return
        name, accepted = QInputDialog.getText(
            self,
            "Renombrar perfil",
            "Nombre visible:",
            text=profile.display_name or profile.brave_display_name,
        )
        if accepted:
            self.controller.rename_profile(profile_id, name)

    def _color_dialog(self, profile_id: str) -> None:
        from PySide6.QtGui import QColor

        profile = self.controller.profile(profile_id)
        if profile is None:
            return
        chosen = QColorDialog.getColor(QColor(profile.color), self, "Color del perfil")
        if chosen.isValid():
            self.controller.update_profile(profile_id, color=chosen.name())

    def _set_tray_enabled(self, enabled: bool) -> None:
        self._tray_enabled = enabled
        self.database.set_setting("tray_enabled", "1" if enabled else "0")
        if enabled:
            if self._tray is None:
                self._tray = TrayIcon(self)
                self._tray.activateProfileRequested.connect(self._on_profile_clicked)
                self._tray.nextProfileRequested.connect(lambda: self._cycle_profile(1))
                self._tray.prevProfileRequested.connect(lambda: self._cycle_profile(-1))
                self._tray.refreshRequested.connect(self.controller.refresh)
                self._tray.toggleWindowRequested.connect(self._toggle_visible)
                self._tray.quitRequested.connect(self._quit)
                self._tray.set_profiles(self.controller.profiles)
            self._tray.show()
        elif self._tray is not None:
            self._tray.hide()

    def _toggle_visible(self) -> None:
        if self.isVisible() and not self.isMinimized():
            self.hide()
        else:
            self.showNormal()
            self.raise_()
            self.activateWindow()

    def _show_help(self) -> None:
        HelpDialog(self).exec()

    def _show_status(self, message: str) -> None:
        self.statusBar().showMessage(message, 6000)

    def _quit(self) -> None:
        self.controller.stop()
        if self.grabber is not None:
            self.grabber.stop()
        QApplication.instance().quit()

    def closeEvent(self, event) -> None:  # noqa: N802 (API de Qt)
        if self._tray_enabled and self._tray is not None and self._tray.isVisible():
            self.hide()
            event.ignore()
            return
        self.controller.stop()
        if self.grabber is not None:
            self.grabber.stop()
        event.accept()
