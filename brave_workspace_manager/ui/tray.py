"""System tray icon: quick switching between profiles."""

from __future__ import annotations

from PySide6.QtCore import QTimer, Signal
from PySide6.QtGui import QCursor, QIcon
from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon

from ..i18n import tr
from ..models import Profile
from . import icons

AVATAR_SIZE = 22


def profile_entry(profile: Profile) -> str:
    """Text of a profile in the menu: its name and, when known, its tabs."""
    if profile.is_open and profile.tab_count:
        tabs = (
            tr("card.tabs.one")
            if profile.tab_count == 1
            else tr("card.tabs.many", count=profile.tab_count)
        )
        return f"{profile.label}  ·  {tabs}"
    return profile.label


class TrayIcon(QSystemTrayIcon):
    """Tray icon with a menu to jump between profiles.

    Cinnamon hosts tray icons through StatusNotifierItem, where Qt only
    receives single clicks; a double click is therefore detected here as two
    clicks within the system double-click interval.
    """

    activateProfileRequested = Signal(str)
    showWindowRequested = Signal()
    showMaximizedRequested = Signal()
    quitRequested = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setIcon(QIcon(icons.app_pixmap()))
        self.setToolTip("Brave Workspace Manager")
        self._profiles: list[Profile] = []
        self._active_id: str | None = None
        self._signature: tuple = ()
        self._dirty = False
        self._menu = QMenu()
        self._menu.aboutToHide.connect(self._rebuild_if_dirty)
        self._click_timer = QTimer(self)
        self._click_timer.setSingleShot(True)
        self._click_timer.timeout.connect(self._single_click)
        self._build_menu()
        self.setContextMenu(self._menu)
        self.activated.connect(self._on_activated)

    # ------------------------------------------------------------- the menu

    def _build_menu(self) -> None:
        self._menu.clear()
        open_profiles = [p for p in self._profiles if p.is_open]
        closed_profiles = [p for p in self._profiles if not p.is_open]

        if not self._profiles:
            empty = self._menu.addAction(tr("tray.no_profiles"))
            empty.setEnabled(False)
        for profile in open_profiles:
            self._add_profile(self._menu, profile)
        if closed_profiles:
            if open_profiles:
                self._menu.addSeparator()
            others = self._menu.addMenu(tr("tray.other_profiles"))
            for profile in closed_profiles:
                self._add_profile(others, profile)

        self._menu.addSeparator()
        show = self._menu.addAction(tr("tray.show_window"))
        show.triggered.connect(self.showWindowRequested.emit)
        quit_action = self._menu.addAction(tr("tray.quit"))
        quit_action.triggered.connect(self.quitRequested.emit)
        self._dirty = False

    def _add_profile(self, menu: QMenu, profile: Profile) -> None:
        action = menu.addAction(
            QIcon(icons.avatar_pixmap(profile, AVATAR_SIZE)), profile_entry(profile)
        )
        if profile.id == self._active_id:
            action.setCheckable(True)
            action.setChecked(True)
        action.triggered.connect(
            lambda _checked=False, profile_id=profile.id: self.activateProfileRequested.emit(
                profile_id
            )
        )

    def set_profiles(self, profiles: list[Profile], active_id: str | None = None) -> None:
        """Updates the menu; it is only rebuilt when something visible changed."""
        self._profiles = list(profiles)
        self._active_id = active_id
        signature = (
            active_id,
            tuple(
                (p.id, p.label, p.is_open, p.tab_count, p.color, p.custom_image) for p in profiles
            ),
        )
        if signature == self._signature:
            return
        self._signature = signature
        if self._menu.isVisible():
            self._dirty = True
        else:
            self._build_menu()

    def retranslate(self) -> None:
        """Rebuilds the menu in the active language."""
        self._build_menu()

    def _rebuild_if_dirty(self) -> None:
        if self._dirty:
            QTimer.singleShot(0, self._build_menu)

    @property
    def menu(self) -> QMenu:
        return self._menu

    # --------------------------------------------------------------- clicks

    def _on_activated(self, reason) -> None:
        if reason == QSystemTrayIcon.DoubleClick:
            self._click_timer.stop()
            self.showMaximizedRequested.emit()
        elif reason == QSystemTrayIcon.Trigger:
            if self._click_timer.isActive():
                self._click_timer.stop()
                self.showMaximizedRequested.emit()
            else:
                self._click_timer.start(QApplication.doubleClickInterval())

    def _single_click(self) -> None:
        """A single left click shows the same menu as the right click."""
        self._menu.popup(QCursor.pos())
