"""Final card of the gallery: the Brave windows that have no profile yet."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from ..i18n import tr
from ..models import Profile, WindowInfo


class UnassignedCard(QFrame):
    """Card that groups the windows the app could not attribute to a profile."""

    saveProfileRequested = Signal(int, str)
    assignRequested = Signal(int, str)
    windowActionRequested = Signal(int, str)

    HEIGHT = 148

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("Card")
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setFixedHeight(self.HEIGHT)
        self._windows: list[WindowInfo] = []
        self._profiles: list[Profile] = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(8)

        top = QHBoxLayout()
        top.setSpacing(10)
        self._title = QLabel()
        self._title.setStyleSheet("font-weight: 600; font-size: 14px;")
        top.addWidget(self._title)
        top.addStretch(1)
        self._window_combo = QComboBox()
        self._window_combo.setMinimumWidth(240)
        self._window_combo.setMaximumWidth(460)
        self._window_combo.setSizeAdjustPolicy(QComboBox.AdjustToContents)
        self._window_combo.currentIndexChanged.connect(self._on_window_changed)
        top.addWidget(self._window_combo)
        layout.addLayout(top)

        self._note = QLabel()
        self._note.setObjectName("Muted")
        self._note.setWordWrap(True)
        layout.addWidget(self._note)

        bottom = QHBoxLayout()
        bottom.setSpacing(8)

        self._save_button = QPushButton()
        self._save_button.clicked.connect(self._emit_save)
        bottom.addWidget(self._save_button)

        self._assign_combo = QComboBox()
        self._assign_combo.setMinimumWidth(200)
        self._assign_combo.currentIndexChanged.connect(self._on_assign)
        bottom.addWidget(self._assign_combo)

        bottom.addStretch(1)

        self._activate_button = QPushButton()
        self._activate_button.clicked.connect(lambda: self._emit_action("activate"))
        bottom.addWidget(self._activate_button)

        self._minimize_button = QPushButton()
        self._minimize_button.clicked.connect(lambda: self._emit_action("minimize"))
        bottom.addWidget(self._minimize_button)

        self._close_button = QPushButton()
        self._close_button.setObjectName("Danger")
        self._close_button.clicked.connect(lambda: self._emit_action("close"))
        bottom.addWidget(self._close_button)

        layout.addLayout(bottom)
        self.retranslate()

    # -------------------------------------------------------------- content

    def set_windows(self, windows: list[WindowInfo], profiles: list[Profile]) -> None:
        """Updates the card with the windows that have no profile."""
        self._windows = list(windows)
        self._profiles = list(profiles)
        self._window_combo.blockSignals(True)
        self._window_combo.clear()
        for window in self._windows:
            etiqueta = window.title or tr("card.no_windows")
            if window.tab_titles:
                etiqueta = f"{etiqueta} — {window.tabs_text}"
            self._window_combo.addItem(etiqueta, window.window_id)
        self._window_combo.blockSignals(False)

        self._assign_combo.blockSignals(True)
        self._assign_combo.clear()
        self._assign_combo.addItem(tr("unassigned.assign_none"), "")
        for profile in self._profiles:
            self._assign_combo.addItem(profile.label, profile.id)
        self._assign_combo.blockSignals(False)

        self.retranslate()

    def retranslate(self) -> None:
        """Rebuilds the texts of the card in the active language."""
        count = len(self._windows)
        self._title.setText(tr("unassigned.count", count=count))
        self._note.setText(tr("unassigned.note") if count else tr("unassigned.empty"))
        self._save_button.setText(tr("unassigned.save_profile"))
        self._save_button.setToolTip(tr("unassigned.save_profile_tip"))
        self._activate_button.setText(tr("card.action.activate"))
        self._minimize_button.setText(tr("card.action.minimize"))
        self._close_button.setText(tr("card.action.close"))
        self._save_button.setEnabled(bool(self._windows))
        self._activate_button.setEnabled(bool(self._windows))
        self._minimize_button.setEnabled(bool(self._windows))
        self._close_button.setEnabled(bool(self._windows))
        self._assign_combo.setEnabled(bool(self._windows) and bool(self._profiles))

    # -------------------------------------------------------------- actions

    def _selected_window(self) -> WindowInfo | None:
        if not self._windows:
            return None
        window_id = self._window_combo.currentData()
        return next((w for w in self._windows if w.window_id == window_id), self._windows[0])

    def _on_window_changed(self, _index: int) -> None:
        self._save_button.setEnabled(self._selected_window() is not None)

    def _emit_save(self) -> None:
        window = self._selected_window()
        if window is None:
            return
        self.saveProfileRequested.emit(window.window_id, window.title)

    def _on_assign(self, index: int) -> None:
        profile_id = self._assign_combo.itemData(index)
        window = self._selected_window()
        if not profile_id or window is None:
            return
        self.assignRequested.emit(window.window_id, str(profile_id))
        self._assign_combo.blockSignals(True)
        self._assign_combo.setCurrentIndex(0)
        self._assign_combo.blockSignals(False)

    def _emit_action(self, action: str) -> None:
        window = self._selected_window()
        if window is None:
            return
        self.windowActionRequested.emit(window.window_id, action)
