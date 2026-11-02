"""Galeria de perfiles: rejilla responsive y resumen siempre visible."""

from __future__ import annotations

import math

from PySide6.QtCore import QPoint, QSize, Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QLabel,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from ..models import Profile, WindowInfo
from .profile_tab import ProfileTab
from .theme import BORDER

TILE_MIN_WIDTH = 152
TILE_MAX_WIDTH = 200
TILE_HEIGHT = 132
SPACING = 12


def grid_geometry(available: int, count: int) -> tuple[int, int, int, int]:
    """Reparte las fichas en una rejilla centrada.

    Devuelve el numero de columnas, el ancho de cada ficha, el desplazamiento
    horizontal del conjunto y el numero de filas. La rejilla usa el ancho
    disponible, asi que se reorganiza sola al cambiar el tamano de la ventana.
    """
    if count <= 0 or available <= 0:
        return 0, 0, 0, 0
    columns = max(1, (available + SPACING) // (TILE_MIN_WIDTH + SPACING))
    tile_width = (available - SPACING * (columns - 1)) // columns
    tile_width = max(TILE_MIN_WIDTH, min(TILE_MAX_WIDTH, tile_width))
    grid_width = columns * tile_width + SPACING * (columns - 1)
    offset = max(0, (available - grid_width) // 2)
    rows = math.ceil(count / columns)
    return columns, tile_width, offset, rows


def gallery_height(available: int) -> int:
    """Altura de la galeria: filas completas que caben en el espacio disponible."""
    row = TILE_HEIGHT + SPACING
    rows = max(2, min(3, int(available) // row))
    return rows * row


class ProfileSummary(QFrame):
    """Resumen de los perfiles: siempre visible y pegado a la izquierda."""

    WIDTH = 224

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("Card")
        self.setFixedWidth(self.WIDTH)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Maximum)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(10)

        title = QLabel("Resumen")
        title.setObjectName("SummaryTitle")
        layout.addWidget(title)

        grid = QGridLayout()
        grid.setHorizontalSpacing(14)
        grid.setVerticalSpacing(6)
        self._values: dict[str, QLabel] = {}
        rows = (
            ("total", "Perfiles"),
            ("open", "Abiertos"),
            ("closed", "Cerrados"),
            ("favorites", "Favoritos"),
            ("windows", "Ventanas de Brave"),
            ("unassigned", "Sin asignar"),
        )
        for row, (key, text) in enumerate(rows):
            label = QLabel(text)
            label.setObjectName("SummaryLabel")
            value = QLabel("0")
            value.setObjectName("SummaryValue")
            value.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            grid.addWidget(label, row, 0)
            grid.addWidget(value, row, 1)
            self._values[key] = value
        layout.addLayout(grid)

        line = QFrame()
        line.setFixedHeight(1)
        line.setStyleSheet(f"background-color: {BORDER}; border: none;")
        layout.addWidget(line)

        caption = QLabel("Perfil activo")
        caption.setObjectName("SummaryLabel")
        layout.addWidget(caption)

        self._active = QLabel("—")
        self._active.setObjectName("SummaryActive")
        self._active.setWordWrap(True)
        layout.addWidget(self._active)

    def update_summary(
        self,
        profiles: list[Profile],
        windows: list[WindowInfo],
        active_label: str = "",
    ) -> None:
        """Refresca los contadores del resumen."""
        total = len(profiles)
        opened = sum(1 for profile in profiles if profile.is_open)
        favorites = sum(1 for profile in profiles if profile.is_favorite)
        unassigned = sum(1 for window in windows if not window.profile_id)
        self._values["total"].setText(str(total))
        self._values["open"].setText(str(opened))
        self._values["closed"].setText(str(total - opened))
        self._values["favorites"].setText(str(favorites))
        self._values["windows"].setText(str(len(windows)))
        self._values["unassigned"].setText(str(unassigned))
        self._active.setText(active_label or "—")

    def snapshot(self) -> dict[str, str]:
        """Valores que muestra el resumen."""
        return {key: label.text() for key, label in self._values.items()}


class ProfileGallery(QWidget):
    """Rejilla de fichas de perfil que se reajusta sola al ancho disponible."""

    activated = Signal(str)
    doubleClicked = Signal(str)
    contextRequested = Signal(str, QPoint)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._tiles: list[ProfileTab] = []
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)

    @property
    def tiles(self) -> dict[str, ProfileTab]:
        """Fichas actuales indexadas por identificador de perfil."""
        return {tile.profile_id: tile for tile in self._tiles}

    # ------------------------------------------------------------- contenido

    def set_profiles(self, profiles: list[Profile]) -> None:
        """Recrea las fichas de la galeria."""
        for tile in self._tiles:
            tile.hide()
            tile.setParent(None)
            tile.deleteLater()
        self._tiles = []
        for profile in profiles:
            tile = ProfileTab(profile, self)
            tile.activated.connect(self.activated)
            tile.doubleClicked.connect(self.doubleClicked)
            tile.contextRequested.connect(self.contextRequested)
            tile.show()
            self._tiles.append(tile)
        self.relayout()

    def update_profile(self, profile: Profile) -> None:
        """Actualiza una sola ficha sin rehacer la rejilla."""
        for tile in self._tiles:
            if tile.profile_id == profile.id:
                tile.update_profile(profile)
                return

    def set_selected(self, profile_id: str | None) -> None:
        """Resalta la ficha del perfil activo."""
        for tile in self._tiles:
            tile.set_selected(tile.profile_id == profile_id)

    # ------------------------------------------------------------- disposicion

    def relayout(self) -> None:
        """Recalcula las posiciones de las fichas segun el ancho disponible."""
        columns, tile_width, offset, rows = grid_geometry(self.width(), len(self._tiles))
        if columns == 0:
            self._set_minimum_height(0)
            return
        for index, tile in enumerate(self._tiles):
            row, column = divmod(index, columns)
            tile.setGeometry(
                offset + column * (tile_width + SPACING),
                row * (TILE_HEIGHT + SPACING),
                tile_width,
                TILE_HEIGHT,
            )
        self._set_minimum_height(rows * TILE_HEIGHT + (rows - 1) * SPACING)

    def _set_minimum_height(self, height: int) -> None:
        if self.minimumHeight() != height:
            self.setMinimumHeight(height)

    def resizeEvent(self, event) -> None:  # noqa: N802 (API de Qt)
        super().resizeEvent(event)
        self.relayout()

    def showEvent(self, event) -> None:  # noqa: N802 (API de Qt)
        super().showEvent(event)
        self.relayout()

    def minimumSizeHint(self) -> QSize:  # noqa: N802 (API de Qt)
        """La altura la decide la rejilla, no el area que la contiene."""
        return QSize(0, 0)
