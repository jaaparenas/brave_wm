"""Main window: profile gallery, admin panel and header."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QObject, Qt, Signal
from PySide6.QtGui import QColor, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QApplication,
    QColorDialog,
    QComboBox,
    QDialog,
    QFileDialog,
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
from ..i18n import available_languages, current_language, language_name, set_language, tr
from ..x11.grab import ShortcutGrabber
from . import icons
from .admin_panel import DEFAULT_SHORTCUTS, SHORTCUT_ACTIONS, AdminPanel
from .profile_gallery import ProfileGallery, ProfileSummary
from .tray import TrayIcon

IMAGE_FILTER = "Images (*.png *.jpg *.jpeg *.webp *.bmp *.gif);;All files (*)"


class ShortcutRelay(QObject):
    """Safe bridge between the thread that grabs the keys and the interface."""

    triggered = Signal(str)


class HelpDialog(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"{tr('header.help')} · {APP_NAME}")
        self.resize(680, 520)
        layout = QVBoxLayout(self)
        browser = QTextBrowser()
        browser.setOpenExternalLinks(True)
        browser.setHtml(tr("help.body", app=APP_NAME, version=APP_VERSION))
        layout.addWidget(browser)
        close = QPushButton(tr("dialog.close"))
        close.clicked.connect(self.accept)
        layout.addWidget(close, 0, Qt.AlignRight)


class MainWindow(QMainWindow):
    """Main interface of the application."""

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
        self._tabs: dict[str, object] = {}
        self._activate_on_click = True
        self._tray: TrayIcon | None = None
        self._tray_enabled = False
        self._local_shortcuts: list[QShortcut] = []

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

    # ------------------------------------------------------------- building

    def _build_ui(self) -> None:
        central = QWidget()
        root = QVBoxLayout(central)
        root.setContentsMargins(14, 12, 14, 8)
        root.setSpacing(12)

        root.addLayout(self._build_header())

        self._splitter = QSplitter(Qt.Horizontal)
        self._splitter.setChildrenCollapsible(False)
        self._splitter.addWidget(self._build_side_panel())
        self._splitter.addWidget(self._build_gallery_area())
        self._splitter.setStretchFactor(0, 0)
        self._splitter.setStretchFactor(1, 1)
        self._splitter.setSizes([470, 760])
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
        self._subtitle = QLabel()
        self._subtitle.setObjectName("HeaderSubtitle")
        titles.addWidget(self._subtitle)
        header.addLayout(titles)
        header.addStretch(1)

        self._language_combo = QComboBox()
        self._language_combo.setToolTip(tr("header.language"))
        for code in available_languages():
            self._language_combo.addItem(language_name(code), code)
        index = self._language_combo.findData(current_language())
        self._language_combo.setCurrentIndex(max(0, index))
        self._language_combo.currentIndexChanged.connect(self._on_language_changed)
        header.addWidget(self._language_combo)

        self._refresh_button = QPushButton()
        self._refresh_button.clicked.connect(self.controller.refresh)
        header.addWidget(self._refresh_button)

        self._help_button = QPushButton()
        self._help_button.clicked.connect(self._show_help)
        header.addWidget(self._help_button)
        return header

    def _build_side_panel(self) -> QWidget:
        """Left column: summary on top and the admin table below, always visible."""
        panel = QWidget()
        panel.setMinimumWidth(420)
        panel.setMaximumWidth(560)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        self._summary = ProfileSummary()
        layout.addWidget(self._summary)

        self._admin_panel = AdminPanel()
        layout.addWidget(self._admin_panel, 1)
        return panel

    def _build_gallery_area(self) -> QWidget:
        """Right column: the gallery of profiles."""
        area = QWidget()
        layout = QVBoxLayout(area)
        layout.setContentsMargins(0, 0, 0, 0)

        self._gallery = ProfileGallery()
        self._gallery.activated.connect(self._on_profile_clicked)
        self._gallery.doubleClicked.connect(self.controller.launch_profile)
        self._gallery.contextRequested.connect(self._show_profile_menu)
        self._gallery.windowActionRequested.connect(self._on_window_action)
        self._gallery.reordered.connect(self._on_profiles_reordered)
        self._gallery.saveProfileRequested.connect(self._on_save_window_as_profile)
        self._gallery.assignRequested.connect(self.controller.assign_window)
        self._gallery.unassignedActionRequested.connect(self._on_unassigned_action)

        self._gallery_scroll = QScrollArea()
        self._gallery_scroll.setWidgetResizable(True)
        self._gallery_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._gallery_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self._gallery_scroll.setWidget(self._gallery)
        self._gallery_scroll.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout.addWidget(self._gallery_scroll)
        return area

    # -------------------------------------------------------------- signals

    def _connect_controller(self) -> None:
        self.controller.profilesChanged.connect(self._rebuild_profiles)
        self.controller.windowsChanged.connect(self._refresh_state)
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
        panel.imageRequested.connect(self._on_image_requested)
        panel.imageCleared.connect(self._on_image_cleared)

    def _load_settings(self) -> None:
        settings = {
            "poll_interval": self.database.get_setting("poll_interval", "2000"),
            "activate_on_click": self.database.get_setting("activate_on_click", "1"),
            "hotkeys_enabled": self.database.get_setting("hotkeys_enabled", "1"),
            "tray_enabled": self.database.get_setting("tray_enabled", "0"),
            "autostart": self.database.get_setting("autostart", "0"),
            "read_tabs": self.database.get_setting("read_tabs", "1"),
        }
        self._activate_on_click = settings["activate_on_click"] == "1"
        self._admin_panel.set_settings(settings)
        self.controller.set_poll_interval(int(settings["poll_interval"]))
        self.controller.set_read_tabs(settings["read_tabs"] == "1")
        self._admin_panel.set_shortcuts(self._shortcut_bindings())
        self._set_tray_enabled(settings["tray_enabled"] == "1")
        language = current_language()
        index = self._language_combo.findData(language)
        if index >= 0:
            self._language_combo.blockSignals(True)
            self._language_combo.setCurrentIndex(index)
            self._language_combo.blockSignals(False)
        if settings["hotkeys_enabled"] == "1":
            self._apply_shortcuts()
        self.apply_language()

    def _shortcut_bindings(self) -> dict[str, str]:
        bindings = dict(DEFAULT_SHORTCUTS)
        for action, _ in SHORTCUT_ACTIONS:
            stored = self.database.get_setting(f"shortcut.{action}")
            if stored:
                bindings[action] = stored
        return bindings

    def _install_local_shortcuts(self) -> None:
        """Shortcuts that work when the window has the focus."""
        for shortcut in self._local_shortcuts:
            shortcut.setEnabled(False)
            shortcut.deleteLater()
        self._local_shortcuts = []
        for action, sequence in self._shortcut_bindings().items():
            shortcut = QShortcut(QKeySequence(sequence), self)
            shortcut.activated.connect(lambda a=action: self._on_shortcut(a))
            self._local_shortcuts.append(shortcut)

    def start(self) -> None:
        """Starts the global keyboard grabs, which need the grabber."""
        self._install_local_shortcuts()
        if self.database.get_setting("hotkeys_enabled", "1") == "1":
            self._apply_shortcuts()

    # ------------------------------------------------------------ rendering

    def _rebuild_profiles(self) -> None:
        self._gallery.set_profiles(self.controller.profiles)
        self._tabs = self._gallery.tiles
        if self._tray is not None:
            self._tray.set_profiles(self.controller.profiles)
        self._refresh_state()

    def _refresh_state(self) -> None:
        """Pushes the current state of the app into every widget."""
        selected = self.controller.selected_profile_id
        profile = self.controller.profile(selected) if selected else None
        if profile is None and self.controller.profiles:
            profile = self.controller.profiles[0]
            self.controller.select(profile.id)

        for perfil in self.controller.profiles:
            tile = self._gallery.tiles.get(perfil.id)
            if tile is not None:
                tile.update_profile(perfil)
        self._gallery.set_windows(
            {
                perfil.id: self.controller.windows_for(perfil.id)
                for perfil in self.controller.profiles
            }
        )
        self._gallery.set_unassigned(self.controller.unassigned_windows(), self.controller.profiles)
        self._gallery.set_selected(self.controller.selected_profile_id)
        self._admin_panel.set_profiles(self.controller.profiles)
        self._summary.update_summary(
            self.controller.profiles,
            self.controller.windows,
            profile.label if profile else "",
        )
        self._status_label.setText(
            tr(
                "status.backend",
                backend=self.controller.backend.name,
                session=session_type(),
                desktop=desktop_environment() or tr("status.desktop_unknown"),
            )
        )

    def _on_selection_changed(self, profile_id: str) -> None:
        self._admin_panel.select_profile(profile_id)
        self._refresh_state()

    # -------------------------------------------------------------- actions

    def _on_profile_clicked(self, profile_id: str) -> None:
        self.controller.select(profile_id)
        if self._activate_on_click:
            self.controller.activate_profile(profile_id)

    def _on_window_action(self, _profile_id: str, window_id: int, action: str) -> None:
        self.controller.window_action(window_id, action)

    def _on_unassigned_action(self, window_id: int, action: str) -> None:
        self.controller.window_action(window_id, action)

    def _on_profiles_reordered(self, profile_ids: list) -> None:
        self.controller.reorder_profiles(list(profile_ids))
        self._show_status(tr("status.reordered"))

    def _on_save_window_as_profile(self, window_id: int, title: str) -> None:
        """Creates a profile of the app for a window that had none."""
        name, accepted = QInputDialog.getText(
            self,
            tr("unassigned.profile_title"),
            tr("unassigned.profile_label"),
            text=title,
        )
        if not accepted:
            return
        profile_id = self.controller.save_window_as_profile(window_id, name)
        if profile_id:
            self.controller.select(profile_id)

    def _on_color_requested(self, profile_id: str, color: str) -> None:
        self.controller.update_profile(profile_id, color=color)

    def _on_image_requested(self, profile_id: str) -> None:
        """Asks for an image file and links it to the profile."""
        path, _ = QFileDialog.getOpenFileName(
            self,
            tr("admin.pick_image"),
            str(Path.home()),
            IMAGE_FILTER,
        )
        if not path:
            return
        if not self.controller.set_profile_image(profile_id, path):
            self._show_status(tr("status.image_missing"))
            return
        self._show_status(tr("status.image_saved"))

    def _on_image_cleared(self, profile_id: str) -> None:
        self.controller.set_profile_image(profile_id, None)
        self._show_status(tr("status.image_saved"))

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
            self._set_tray_enabled(value == "1")
        elif key == "autostart":
            if value == "1":
                autostart.enable(autostart.python_command())
            else:
                autostart.disable()
        elif key == "read_tabs":
            self.controller.set_read_tabs(value == "1")

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
            self._show_status(
                tr("status.shortcut_conflict", detail=detail)
                if detail
                else tr("status.shortcut_conflict_generic")
            )
        else:
            self._show_status(tr("status.shortcuts_ok"))

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
        activate = menu.addAction(tr("menu.activate"))
        activate.triggered.connect(lambda: self.controller.activate_profile(profile_id))
        if not profile.is_virtual:
            open_action = menu.addAction(tr("menu.open"))
            open_action.triggered.connect(lambda: self.controller.launch_profile(profile_id))
        adopt = menu.addAction(tr("menu.adopt"))
        adopt.triggered.connect(lambda: self.controller.adopt_active_window(profile_id))

        menu.addSeparator()
        rename = menu.addAction(tr("menu.rename"))
        rename.triggered.connect(lambda: self._rename_dialog(profile_id))
        color = menu.addAction(tr("menu.color"))
        color.triggered.connect(lambda: self._color_dialog(profile_id))

        icon_menu = menu.addMenu(tr("menu.icon"))
        for name in icons.GLYPH_NAMES:
            action = icon_menu.addAction(
                icons.glyph_pixmap(name, "#e7eaf0", 16), tr(f"icon.{name}")
            )
            action.triggered.connect(
                lambda _checked=False, value=name: self.controller.update_profile(
                    profile_id, icon=value
                )
            )

        image = menu.addAction(tr("menu.image"))
        image.triggered.connect(lambda: self._on_image_requested(profile_id))

        favorite = menu.addAction(
            tr("menu.favorite_remove") if profile.is_favorite else tr("menu.favorite_add")
        )
        favorite.triggered.connect(
            lambda: self.controller.update_profile(profile_id, is_favorite=not profile.is_favorite)
        )

        menu.addSeparator()
        up = menu.addAction(tr("menu.up"))
        up.triggered.connect(lambda: self.controller.move_profile(profile_id, -1))
        down = menu.addAction(tr("menu.down"))
        down.triggered.connect(lambda: self.controller.move_profile(profile_id, 1))
        reset = menu.addAction(tr("menu.reset"))
        reset.triggered.connect(lambda: self.controller.reset_profile(profile_id))
        menu.exec(position)

    def _rename_dialog(self, profile_id: str) -> None:
        profile = self.controller.profile(profile_id)
        if profile is None:
            return
        name, accepted = QInputDialog.getText(
            self,
            tr("dialog.rename.title"),
            tr("dialog.rename.label"),
            text=profile.display_name or profile.brave_display_name,
        )
        if accepted:
            self.controller.rename_profile(profile_id, name)

    def _color_dialog(self, profile_id: str) -> None:
        profile = self.controller.profile(profile_id)
        if profile is None:
            return
        chosen = QColorDialog.getColor(QColor(profile.color), self, tr("dialog.color.title"))
        if chosen.isValid():
            self.controller.update_profile(profile_id, color=chosen.name())

    # --------------------------------------------------------------- language

    def _on_language_changed(self, _index: int) -> None:
        code = self._language_combo.currentData()
        if not code:
            return
        set_language(code)
        self.database.set_setting("language", code)
        self.apply_language()

    def apply_language(self) -> None:
        """Rebuilds every text of the interface in the active language."""
        self._refresh_button.setText(tr("header.refresh"))
        self._help_button.setText(tr("header.help"))
        self._language_combo.setToolTip(tr("header.language"))
        self._subtitle.setText(tr("app.subtitle"))
        for child in self.findChildren(QWidget):
            retranslate = getattr(child, "retranslate", None)
            if callable(retranslate):
                retranslate()
        if self._tray is not None:
            self._tray.retranslate()
        self.controller.refresh()

    # ------------------------------------------------------------------ tray

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

    def closeEvent(self, event) -> None:  # noqa: N802 (Qt API)
        if self._tray_enabled and self._tray is not None and self._tray.isVisible():
            self.hide()
            event.ignore()
            return
        self.controller.stop()
        if self.grabber is not None:
            self.grabber.stop()
        event.accept()
