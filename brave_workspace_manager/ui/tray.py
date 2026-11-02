"""System tray icon."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QMenu, QSystemTrayIcon

from ..i18n import tr
from ..models import Profile
from . import icons


class TrayIcon(QSystemTrayIcon):
    """Quick access to the profiles from the system tray."""

    activateProfileRequested = Signal(str)
    nextProfileRequested = Signal()
    prevProfileRequested = Signal()
    refreshRequested = Signal()
    toggleWindowRequested = Signal()
    quitRequested = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setIcon(icons.app_pixmap())
        self.setToolTip("Brave Workspace Manager")
        self._profiles: list[Profile] = []
        self._menu = QMenu()
        self._build_menu()
        self.setContextMenu(self._menu)
        self.activated.connect(self._on_activated)

    def _build_menu(self) -> None:
        self._menu.clear()
        show = QAction(tr("tray.toggle_window"), self._menu)
        show.triggered.connect(self.toggleWindowRequested.emit)
        self._menu.addAction(show)

        self._menu.addSeparator()
        self._profile_actions = []
        for index in range(9):
            action = QAction(f"{index + 1}", self._menu)
            action.triggered.connect(
                lambda _checked=False, position=index: self._activate_position(position)
            )
            self._menu.addAction(action)
            self._profile_actions.append(action)

        self._menu.addSeparator()
        next_action = QAction(tr("tray.next_profile"), self._menu)
        next_action.triggered.connect(self.nextProfileRequested.emit)
        self._menu.addAction(next_action)
        previous_action = QAction(tr("tray.prev_profile"), self._menu)
        previous_action.triggered.connect(self.prevProfileRequested.emit)
        self._menu.addAction(previous_action)

        self._menu.addSeparator()
        refresh = QAction(tr("tray.refresh"), self._menu)
        refresh.triggered.connect(self.refreshRequested.emit)
        self._menu.addAction(refresh)

        quit_action = QAction(tr("tray.quit"), self._menu)
        quit_action.triggered.connect(self.quitRequested.emit)
        self._menu.addAction(quit_action)

    def retranslate(self) -> None:
        """Rebuilds the texts of the tray menu in the active language."""
        self._build_menu()
        self.set_profiles(self._profiles)

    def set_profiles(self, profiles: list[Profile]) -> None:
        self._profiles = profiles
        for index, action in enumerate(self._profile_actions):
            if index < len(profiles):
                profile = profiles[index]
                action.setText(f"{index + 1}. {profile.label}")
                action.setVisible(True)
                action.setEnabled(profile.is_open)
            else:
                action.setVisible(False)

    def _activate_position(self, position: int) -> None:
        if 0 <= position < len(self._profiles):
            self.activateProfileRequested.emit(self._profiles[position].id)

    def _on_activated(self, reason) -> None:
        if reason == QSystemTrayIcon.Trigger:
            self.toggleWindowRequested.emit()
