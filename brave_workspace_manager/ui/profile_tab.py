"""Ficha de perfil mostrada en la galeria."""

from __future__ import annotations

from PySide6.QtCore import QPoint, Qt, Signal
from PySide6.QtGui import QFontMetrics, QPixmap
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from ..models import Profile
from . import icons
from .theme import ACCENT, BORDER, SURFACE, SURFACE_ALT


class ProfileTab(QFrame):
    """Ficha de un perfil dentro de la galeria."""

    activated = Signal(str)
    contextRequested = Signal(str, QPoint)
    doubleClicked = Signal(str)

    WIDTH = 168
    HEIGHT = 132
    AVATAR = 56

    def __init__(self, profile: Profile, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.profile_id = profile.id
        self.setObjectName("Card")
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumHeight(self.HEIGHT)
        self._selected = False
        self._color = profile.color
        self._full_name = ""
        self._full_status = ""

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(4)

        self._accent = QFrame()
        self._accent.setFixedHeight(3)
        self._accent.setFrameShape(QFrame.NoFrame)
        layout.addWidget(self._accent)

        top = QHBoxLayout()
        top.setContentsMargins(0, 0, 0, 0)
        top.setSpacing(0)
        self._favorite = QLabel()
        self._favorite.setFixedSize(16, 16)
        top.addWidget(self._favorite, 0, Qt.AlignTop)
        self._avatar = QLabel()
        self._avatar.setFixedSize(self.AVATAR, self.AVATAR)
        top.addWidget(self._avatar, 1, Qt.AlignHCenter)
        self._filler = QLabel()
        self._filler.setFixedSize(16, 16)
        top.addWidget(self._filler, 0, Qt.AlignTop)
        layout.addLayout(top)

        self._name = QLabel()
        self._name.setAlignment(Qt.AlignCenter)
        self._name.setStyleSheet("font-weight: 600;")
        self._name.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        self._name.setToolTip(profile.directory_name)
        layout.addWidget(self._name)

        self._status = QLabel()
        self._status.setAlignment(Qt.AlignCenter)
        self._status.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        layout.addWidget(self._status)

        layout.addStretch(1)
        self.update_profile(profile)

    # ------------------------------------------------------------- contenido

    def update_profile(self, profile: Profile) -> None:
        self.profile_id = profile.id
        self._color = profile.color
        self._accent.setStyleSheet(f"background-color: {profile.color}; border-radius: 2px;")
        self._apply_style()
        self._avatar.setPixmap(icons.avatar_pixmap(profile, self.AVATAR))
        self._full_name = profile.label
        self._name.setToolTip(f"{profile.label}  ·  {profile.directory_name}")
        self._full_status = profile.status_text
        self._status.setObjectName("StatusOk" if profile.is_open else "StatusOff")
        if profile.is_favorite:
            self._favorite.setPixmap(icons.glyph_pixmap("star", "#ffd43b", 16))
        else:
            self._favorite.setPixmap(QPixmap())
        self._refresh_texts()

    def set_selected(self, selected: bool) -> None:
        """Marca la ficha como activa en la galeria."""
        if selected == self._selected:
            return
        self._selected = selected
        self._apply_style()

    def _apply_style(self) -> None:
        border = ACCENT if self._selected else BORDER
        thickness = 2 if self._selected else 1
        background = SURFACE_ALT if self._selected else SURFACE
        self.setStyleSheet(
            f"QFrame#Card {{ background-color: {background}; border: {thickness}px solid {border};"
            f" border-radius: 10px; }}"
            "QLabel { background: transparent; border: none; }"
        )

    def _refresh_texts(self) -> None:
        self._set_elided(self._name, self._full_name)
        self._set_elided(self._status, self._full_status)

    def _set_elided(self, label: QLabel, text: str) -> None:
        metrics = QFontMetrics(label.font())
        elided = metrics.elidedText(text, Qt.ElideRight, max(24, label.width()))
        if label.text() != elided:
            label.setText(elided)

    def resizeEvent(self, event) -> None:  # noqa: N802 (API de Qt)
        super().resizeEvent(event)
        self._refresh_texts()

    # ------------------------------------------------------------- interaccion

    def mousePressEvent(self, event) -> None:  # noqa: N802 (API de Qt)
        if event.button() == Qt.LeftButton:
            self.activated.emit(self.profile_id)
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event) -> None:  # noqa: N802 (API de Qt)
        self.doubleClicked.emit(self.profile_id)
        super().mouseDoubleClickEvent(event)

    def contextMenuEvent(self, event) -> None:  # noqa: N802 (API de Qt)
        self.contextRequested.emit(self.profile_id, event.globalPos())
        super().contextMenuEvent(event)
