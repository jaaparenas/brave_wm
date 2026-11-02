"""Tarjeta de perfil mostrada en la barra superior."""

from __future__ import annotations

from PySide6.QtCore import QPoint, Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from ..models import Profile
from . import icons
from .theme import SURFACE


class ProfileTab(QFrame):
    """Representa un perfil en la barra de perfiles."""

    activated = Signal(str)
    contextRequested = Signal(str, QPoint)
    doubleClicked = Signal(str)

    WIDTH = 196
    HEIGHT = 68

    def __init__(self, profile: Profile, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.profile_id = profile.id
        self.setObjectName("Card")
        self.setFixedWidth(self.WIDTH)
        self.setFixedHeight(self.HEIGHT)
        self.setCursor(Qt.PointingHandCursor)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(10)

        self._accent = QFrame()
        self._accent.setFixedWidth(4)
        self._accent.setFrameShape(QFrame.NoFrame)
        layout.addWidget(self._accent)

        self._avatar = QLabel()
        self._avatar.setFixedSize(36, 36)
        layout.addWidget(self._avatar)

        column = QVBoxLayout()
        column.setSpacing(2)
        column.setContentsMargins(0, 0, 0, 0)
        self._name = QLabel()
        self._name.setStyleSheet("font-weight: 600;")
        self._name.setToolTip(profile.directory_name)
        column.addWidget(self._name)
        self._status = QLabel()
        column.addWidget(self._status)
        layout.addLayout(column, 1)

        self._favorite = QLabel()
        self._favorite.setFixedSize(16, 16)
        layout.addWidget(self._favorite, 0, Qt.AlignTop)

        self.update_profile(profile)

    def update_profile(self, profile: Profile) -> None:
        self.profile_id = profile.id
        color = profile.color
        self._accent.setStyleSheet(f"background-color: {color}; border-radius: 2px;")
        self.setStyleSheet(
            f"QFrame#Card {{ background-color: {SURFACE}; border: 1px solid {color};"
            f" border-radius: 10px; }}"
            "QLabel { background: transparent; border: none; }"
        )
        self._avatar.setPixmap(icons.avatar_pixmap(profile, 36))
        self._name.setText(profile.label)
        self._name.setToolTip(f"{profile.label}  ·  {profile.directory_name}")
        self._status.setText(profile.status_text)
        self._status.setObjectName("StatusOk" if profile.is_open else "StatusOff")
        if profile.is_favorite:
            self._favorite.setPixmap(icons.glyph_pixmap("star", "#ffd43b", 16))
        else:
            self._favorite.setPixmap(QPixmap())

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
