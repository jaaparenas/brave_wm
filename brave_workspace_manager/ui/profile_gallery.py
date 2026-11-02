"""Profile gallery: responsive grid, drag and drop, and the always visible summary."""

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

from ..i18n import tr
from ..models import Profile, WindowInfo
from .profile_tab import MIME_TYPE, ProfileTab
from .theme import BORDER
from .unassigned_card import UnassignedCard

TILE_MIN_WIDTH = 152
TILE_MAX_WIDTH = 200
TILE_HEIGHT = ProfileTab.HEIGHT
EXTRA_HEIGHT = UnassignedCard.HEIGHT
SPACING = 12


def grid_geometry(available: int, count: int) -> tuple[int, int, int, int]:
    """Spreads the cards over a centred grid.

    Returns the number of columns, the width of every card, the horizontal
    offset of the whole set and the number of rows. The grid uses the width
    available, so it rearranges itself when the window is resized.
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
    """Height of the gallery: whole rows that fit in the space available."""
    row = TILE_HEIGHT + SPACING
    rows = max(2, min(3, int(available) // row))
    return rows * row


class ProfileSummary(QFrame):
    """Summary of the profiles: always visible and stuck to the left."""

    WIDTH = 224

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("Card")
        self.setMinimumWidth(self.WIDTH)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(10)

        self._title = QLabel()
        self._title.setObjectName("SummaryTitle")
        layout.addWidget(self._title)

        grid = QGridLayout()
        grid.setHorizontalSpacing(14)
        grid.setVerticalSpacing(6)
        self._values: dict[str, QLabel] = {}
        self._captions: dict[str, QLabel] = {}
        self._caption_keys: dict[str, str] = {}
        rows = (
            ("total", "summary.profiles"),
            ("open", "summary.open"),
            ("closed", "summary.closed"),
            ("favorites", "summary.favorites"),
            ("windows", "summary.windows"),
            ("tabs", "summary.tabs"),
            ("unassigned", "summary.unassigned"),
        )
        for row, (key, text_key) in enumerate(rows):
            label = QLabel()
            label.setObjectName("SummaryLabel")
            value = QLabel("0")
            value.setObjectName("SummaryValue")
            value.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            grid.addWidget(label, row, 0)
            grid.addWidget(value, row, 1)
            self._values[key] = value
            self._captions[key] = label
            self._caption_keys[key] = text_key
        layout.addLayout(grid)

        line = QFrame()
        line.setFixedHeight(1)
        line.setStyleSheet(f"background-color: {BORDER}; border: none;")
        layout.addWidget(line)

        self._caption = QLabel()
        self._caption.setObjectName("SummaryLabel")
        layout.addWidget(self._caption)

        self._active = QLabel("—")
        self._active.setObjectName("SummaryActive")
        self._active.setWordWrap(True)
        layout.addWidget(self._active)
        self.retranslate()

    def retranslate(self) -> None:
        """Rebuilds the texts of the summary in the active language."""
        self._title.setText(tr("summary.title"))
        for key, label in self._captions.items():
            label.setText(tr(self._caption_keys[key]))
        self._caption.setText(tr("summary.active_profile"))
        if self._active.text() in ("", "—"):
            self._active.setText(tr("summary.empty"))

    def update_summary(
        self,
        profiles: list[Profile],
        windows: list[WindowInfo],
        active_label: str = "",
    ) -> None:
        """Refreshes the counters of the summary."""
        total = len(profiles)
        opened = sum(1 for profile in profiles if profile.is_open)
        favorites = sum(1 for profile in profiles if profile.is_favorite)
        unassigned = sum(1 for window in windows if not window.profile_id)
        tabs = sum(window.tab_count for window in windows)
        self._values["total"].setText(str(total))
        self._values["open"].setText(str(opened))
        self._values["closed"].setText(str(total - opened))
        self._values["favorites"].setText(str(favorites))
        self._values["windows"].setText(str(len(windows)))
        self._values["tabs"].setText(str(tabs))
        self._values["unassigned"].setText(str(unassigned))
        self._active.setText(active_label or tr("summary.empty"))

    def snapshot(self) -> dict[str, str]:
        """Values shown by the summary."""
        return {key: label.text() for key, label in self._values.items()}


class ProfileGallery(QWidget):
    """Grid of profile cards that rearranges itself with the available width."""

    activated = Signal(str)
    doubleClicked = Signal(str)
    contextRequested = Signal(str, QPoint)
    windowActionRequested = Signal(str, int, str)
    reordered = Signal(list)
    saveProfileRequested = Signal(int, str)
    assignRequested = Signal(int, str)
    unassignedActionRequested = Signal(int, str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._tiles: list[ProfileTab] = []
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        self.setAcceptDrops(True)

        self._unassigned = UnassignedCard(self)
        self._unassigned.saveProfileRequested.connect(self.saveProfileRequested)
        self._unassigned.assignRequested.connect(self.assignRequested)
        self._unassigned.windowActionRequested.connect(self.unassignedActionRequested)
        self._unassigned.show()

    @property
    def tiles(self) -> dict[str, ProfileTab]:
        """Current cards, indexed by profile id."""
        return {tile.profile_id: tile for tile in self._tiles}

    @property
    def unassigned_card(self) -> UnassignedCard:
        return self._unassigned

    # ------------------------------------------------------------- content

    def set_profiles(self, profiles: list[Profile]) -> None:
        """Keeps the cards in sync with the profiles of the app."""
        existentes = {tile.profile_id: tile for tile in self._tiles}
        nuevos: list[ProfileTab] = []
        for profile in profiles:
            tile = existentes.pop(profile.id, None)
            if tile is None:
                tile = ProfileTab(profile, self)
                tile.activated.connect(self.activated)
                tile.doubleClicked.connect(self.doubleClicked)
                tile.contextRequested.connect(self.contextRequested)
                tile.windowActionRequested.connect(self.windowActionRequested)
                tile.show()
            else:
                tile.update_profile(profile)
            nuevos.append(tile)
        for tile in existentes.values():
            tile.hide()
            tile.setParent(None)
            tile.deleteLater()
        self._tiles = nuevos
        self.relayout()

    def update_profile(self, profile: Profile) -> None:
        """Updates a single card without rebuilding the grid."""
        for tile in self._tiles:
            if tile.profile_id == profile.id:
                tile.update_profile(profile)
                return

    def set_windows(self, windows_by_profile: dict[str, list[WindowInfo]]) -> None:
        """Shares the windows of every profile with its card."""
        for tile in self._tiles:
            tile.set_windows(windows_by_profile.get(tile.profile_id, []))

    def set_unassigned(self, windows: list[WindowInfo], profiles: list[Profile]) -> None:
        """Updates the final card of the gallery."""
        self._unassigned.set_windows(windows, profiles)

    def set_selected(self, profile_id: str | None) -> None:
        """Highlights the card of the active profile."""
        for tile in self._tiles:
            tile.set_selected(tile.profile_id == profile_id)

    # ------------------------------------------------------------- layout

    def relayout(self) -> None:
        """Recalculates the position of the cards with the width available."""
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
        grid_width = columns * tile_width + SPACING * (columns - 1)
        top = rows * (TILE_HEIGHT + SPACING)
        self._unassigned.setGeometry(offset, top, grid_width, EXTRA_HEIGHT)
        self._set_minimum_height(top + EXTRA_HEIGHT)

    def _set_minimum_height(self, height: int) -> None:
        if self.minimumHeight() != height:
            self.setMinimumHeight(height)

    def resizeEvent(self, event) -> None:  # noqa: N802 (Qt API)
        super().resizeEvent(event)
        self.relayout()

    def showEvent(self, event) -> None:  # noqa: N802 (Qt API)
        super().showEvent(event)
        self.relayout()

    def minimumSizeHint(self) -> QSize:  # noqa: N802 (Qt API)
        """The height is decided by the grid, not by the area that holds it."""
        return QSize(0, 0)

    # --------------------------------------------------------- drag & drop

    def dragEnterEvent(self, event) -> None:  # noqa: N802 (Qt API)
        if event.mimeData().hasFormat(MIME_TYPE):
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)

    def dragMoveEvent(self, event) -> None:  # noqa: N802 (Qt API)
        if event.mimeData().hasFormat(MIME_TYPE):
            event.acceptProposedAction()
        else:
            super().dragMoveEvent(event)

    def dropEvent(self, event) -> None:  # noqa: N802 (Qt API)
        if not event.mimeData().hasFormat(MIME_TYPE):
            super().dropEvent(event)
            return
        profile_id = bytes(event.mimeData().data(MIME_TYPE)).decode("utf-8", "replace")
        self._move(profile_id, self._index_at(event.position().toPoint()))
        event.acceptProposedAction()

    def _index_at(self, point: QPoint) -> int:
        """Grid position of a drop, as an index of the cards."""
        columns, tile_width, offset, _ = grid_geometry(self.width(), len(self._tiles))
        if columns == 0:
            return 0
        column = int((point.x() - offset) // (tile_width + SPACING))
        row = int(point.y() // (TILE_HEIGHT + SPACING))
        column = max(0, min(columns - 1, column))
        row = max(0, row)
        return max(0, min(len(self._tiles), row * columns + column))

    def _move(self, profile_id: str, index: int) -> None:
        """Moves a card to another position and tells the app about it."""
        actual = next(
            (i for i, tile in enumerate(self._tiles) if tile.profile_id == profile_id), None
        )
        if actual is None:
            return
        tile = self._tiles.pop(actual)
        index = max(0, min(len(self._tiles), index))
        self._tiles.insert(index, tile)
        self.relayout()
        self.reordered.emit([t.profile_id for t in self._tiles])
