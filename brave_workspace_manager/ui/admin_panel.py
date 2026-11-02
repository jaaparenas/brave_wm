"""Admin panel: profiles, customisation, shortcuts and settings."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QCheckBox,
    QColorDialog,
    QComboBox,
    QFormLayout,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..i18n import tr
from ..models import Profile
from . import icons

SHORTCUT_ACTIONS = (
    ("profile-1", "shortcut.profile.1"),
    ("profile-2", "shortcut.profile.2"),
    ("profile-3", "shortcut.profile.3"),
    ("profile-4", "shortcut.profile.4"),
    ("profile-5", "shortcut.profile.5"),
    ("profile-6", "shortcut.profile.6"),
    ("profile-7", "shortcut.profile.7"),
    ("profile-8", "shortcut.profile.8"),
    ("profile-9", "shortcut.profile.9"),
    ("next-profile", "shortcut.next-profile"),
    ("prev-profile", "shortcut.prev-profile"),
)

DEFAULT_SHORTCUTS = {
    "profile-1": "Ctrl+Alt+1",
    "profile-2": "Ctrl+Alt+2",
    "profile-3": "Ctrl+Alt+3",
    "profile-4": "Ctrl+Alt+4",
    "profile-5": "Ctrl+Alt+5",
    "profile-6": "Ctrl+Alt+6",
    "profile-7": "Ctrl+Alt+7",
    "profile-8": "Ctrl+Alt+8",
    "profile-9": "Ctrl+Alt+9",
    "next-profile": "Ctrl+Alt+Tab",
    "prev-profile": "Ctrl+Alt+Shift+Tab",
}


class AdminPanel(QWidget):
    """Profile edition and general settings."""

    selectionChanged = Signal(str)
    renameRequested = Signal(str, str)
    colorRequested = Signal(str, str)
    iconRequested = Signal(str, str)
    favoriteToggled = Signal(str, bool)
    moveRequested = Signal(str, int)
    resetRequested = Signal(str)
    openProfileRequested = Signal(str)
    manageProfilesRequested = Signal()
    settingChanged = Signal(str, str)
    shortcutChanged = Signal(str, str)
    shortcutResetRequested = Signal()
    imageRequested = Signal(str)
    imageCleared = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._profiles: list[Profile] = []
        self._current: str | None = None
        self._loading = False

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(12)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        content = QWidget()
        self._layout = QVBoxLayout(content)
        self._layout.setContentsMargins(0, 0, 8, 0)
        self._layout.setSpacing(14)

        self._layout.addWidget(self._build_profiles_group())
        self._layout.addWidget(self._build_editor_group())
        self._layout.addWidget(self._build_settings_group())
        self._layout.addWidget(self._build_shortcuts_group())
        self._layout.addStretch(1)

        scroll.setWidget(content)
        root.addWidget(scroll)

    # ------------------------------------------------------------- building

    def _build_profiles_group(self) -> QWidget:
        box = QGroupBox()
        box.setObjectName("Card")
        self._profiles_box = box
        layout = QVBoxLayout(box)
        layout.setContentsMargins(12, 12, 12, 12)

        self._table = QTableWidget(0, 5)
        self._table.verticalHeader().setVisible(False)
        self._table.setSelectionBehavior(QTableWidget.SelectRows)
        self._table.setSelectionMode(QTableWidget.SingleSelection)
        self._table.setEditTriggers(QTableWidget.NoEditTriggers)
        header = self._table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        header.setMinimumSectionSize(48)
        self._table.setMinimumHeight(220)
        self._table.itemSelectionChanged.connect(self._on_table_selection)
        layout.addWidget(self._table)

        buttons = QHBoxLayout()
        self._manage_button = QPushButton()
        self._manage_button.clicked.connect(self.manageProfilesRequested.emit)
        buttons.addWidget(self._manage_button)
        buttons.addStretch(1)
        layout.addLayout(buttons)
        return box

    def _build_editor_group(self) -> QWidget:
        box = QGroupBox()
        box.setObjectName("Card")
        self._editor_box = box
        layout = QVBoxLayout(box)
        layout.setContentsMargins(12, 12, 12, 12)

        form = QFormLayout()
        form.setSpacing(10)

        self._name_edit = QLineEdit()
        self._name_edit.editingFinished.connect(self._on_rename)
        form.addRow("", self._name_edit)

        color_row = QHBoxLayout()
        self._color_button = QPushButton()
        self._color_button.clicked.connect(self._on_pick_color)
        color_row.addWidget(self._color_button)
        self._color_preview = QFrame()
        self._color_preview.setFixedSize(28, 20)
        color_row.addWidget(self._color_preview)
        color_row.addStretch(1)
        form.addRow("", color_row)

        self._icon_combo = QComboBox()
        self._icon_combo.currentIndexChanged.connect(self._on_icon_changed)
        form.addRow("", self._icon_combo)

        image_row = QHBoxLayout()
        self._image_preview = QLabel()
        self._image_preview.setFixedSize(40, 40)
        self._image_preview.setAlignment(Qt.AlignCenter)
        image_row.addWidget(self._image_preview)
        self._image_button = QPushButton()
        self._image_button.clicked.connect(self._emit_image)
        image_row.addWidget(self._image_button)
        self._image_clear = QPushButton()
        self._image_clear.clicked.connect(self._emit_clear_image)
        image_row.addWidget(self._image_clear)
        image_row.addStretch(1)
        form.addRow("", image_row)

        self._favorite_check = QCheckBox()
        self._favorite_check.toggled.connect(self._on_favorite_toggled)
        form.addRow("", self._favorite_check)
        layout.addLayout(form)

        buttons = QHBoxLayout()
        self._move_up = QPushButton()
        self._move_up.clicked.connect(lambda: self._emit_move(-1))
        buttons.addWidget(self._move_up)
        self._move_down = QPushButton()
        self._move_down.clicked.connect(lambda: self._emit_move(1))
        buttons.addWidget(self._move_down)
        self._open_button = QPushButton()
        self._open_button.clicked.connect(self._emit_open)
        buttons.addWidget(self._open_button)
        self._reset_button = QPushButton()
        self._reset_button.clicked.connect(self._emit_reset)
        buttons.addWidget(self._reset_button)
        buttons.addStretch(1)
        layout.addLayout(buttons)
        return box

    def _build_settings_group(self) -> QWidget:
        box = QGroupBox()
        box.setObjectName("Card")
        self._settings_box = box
        layout = QVBoxLayout(box)
        layout.setContentsMargins(12, 12, 12, 12)

        form = QFormLayout()
        form.setSpacing(10)

        self._poll_spin = QSpinBox()
        self._poll_spin.setRange(500, 30000)
        self._poll_spin.setSingleStep(500)
        self._poll_spin.valueChanged.connect(
            lambda value: self.settingChanged.emit("poll_interval", str(value))
        )
        form.addRow("", self._poll_spin)

        self._activate_check = QCheckBox()
        self._activate_check.toggled.connect(
            lambda state: self.settingChanged.emit("activate_on_click", "1" if state else "0")
        )
        form.addRow("", self._activate_check)

        self._hotkeys_check = QCheckBox()
        self._hotkeys_check.toggled.connect(
            lambda state: self.settingChanged.emit("hotkeys_enabled", "1" if state else "0")
        )
        form.addRow("", self._hotkeys_check)

        self._autostart_check = QCheckBox()
        self._autostart_check.toggled.connect(
            lambda state: self.settingChanged.emit("autostart", "1" if state else "0")
        )
        form.addRow("", self._autostart_check)

        self._tabs_check = QCheckBox()
        self._tabs_check.toggled.connect(
            lambda state: self.settingChanged.emit("read_tabs", "1" if state else "0")
        )
        form.addRow("", self._tabs_check)

        layout.addLayout(form)
        return box

    def _build_shortcuts_group(self) -> QWidget:
        box = QGroupBox()
        box.setObjectName("Card")
        self._shortcuts_box = box
        layout = QVBoxLayout(box)
        layout.setContentsMargins(12, 12, 12, 12)

        self._shortcut_table = QTableWidget(0, 2)
        self._shortcut_table.verticalHeader().setVisible(False)
        self._shortcut_table.setEditTriggers(QTableWidget.DoubleClicked)
        self._shortcut_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self._shortcut_table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeToContents
        )
        self._shortcut_table.itemChanged.connect(self._on_shortcut_edited)
        layout.addWidget(self._shortcut_table)

        self._shortcut_note = QLabel()
        self._shortcut_note.setObjectName("Muted")
        self._shortcut_note.setWordWrap(True)
        layout.addWidget(self._shortcut_note)

        self._shortcut_reset = QPushButton()
        self._shortcut_reset.clicked.connect(self.shortcutResetRequested.emit)
        layout.addWidget(self._shortcut_reset)
        return box

    # ------------------------------------------------------------- data

    def set_profiles(self, profiles: list[Profile]) -> None:
        """Fills the table in place, so the refresh does not disturb the user."""
        self._profiles = profiles
        self._loading = True
        self._table.setRowCount(len(profiles))
        for row, profile in enumerate(profiles):
            values = (
                profile.label,
                profile.directory_name,
                profile.status_text,
                str(profile.window_count),
                str(profile.tab_count),
            )
            for column, value in enumerate(values):
                item = self._table.item(row, column)
                if item is None:
                    item = QTableWidgetItem()
                    self._table.setItem(row, column, item)
                if column == 0:
                    item.setData(Qt.UserRole, profile.id)
                if item.text() != value:
                    item.setText(value)
        if profiles:
            index = next((i for i, p in enumerate(profiles) if p.id == self._current), 0)
            if self._table.currentRow() != index:
                self._table.selectRow(index)
            self._load_editor(profiles[index])
        else:
            self._load_editor(None)
        self._loading = False

    def set_shortcuts(self, bindings: dict[str, str]) -> None:
        self._loading = True
        self._shortcut_table.setRowCount(len(SHORTCUT_ACTIONS))
        for row, (action, _) in enumerate(SHORTCUT_ACTIONS):
            name_item = QTableWidgetItem(tr(_label_key(action)))
            name_item.setFlags(Qt.ItemIsEnabled)
            self._shortcut_table.setItem(row, 0, name_item)
            self._shortcut_table.setItem(
                row, 1, QTableWidgetItem(bindings.get(action, DEFAULT_SHORTCUTS[action]))
            )
        self._loading = False

    def set_settings(self, settings: dict[str, str]) -> None:
        self._loading = True
        self._poll_spin.setValue(int(settings.get("poll_interval", 2000)))
        self._activate_check.setChecked(settings.get("activate_on_click", "1") == "1")
        self._hotkeys_check.setChecked(settings.get("hotkeys_enabled", "1") == "1")
        self._autostart_check.setChecked(settings.get("autostart", "0") == "1")
        self._tabs_check.setChecked(settings.get("read_tabs", "1") == "1")
        self._loading = False

    def select_profile(self, profile_id: str) -> None:
        self._current = profile_id
        for row in range(self._table.rowCount()):
            item = self._table.item(row, 0)
            if item is not None and item.data(Qt.UserRole) == profile_id:
                if self._table.currentRow() != row:
                    self._table.selectRow(row)
                self._load_editor(self._profile_by_id(profile_id))
                return

    # ----------------------------------------------------------- retranslate

    def retranslate(self) -> None:
        """Rebuilds every text of the panel in the active language."""
        previous = self._loading
        self._loading = True
        self._profiles_box.setTitle(tr("admin.profiles_group"))
        self._table.setHorizontalHeaderLabels(
            [
                tr("admin.table.profile"),
                tr("admin.table.directory"),
                tr("admin.table.status"),
                tr("admin.table.windows"),
                tr("admin.table.tabs"),
            ]
        )
        self._manage_button.setText(tr("admin.manage_profiles"))
        self._manage_button.setToolTip(tr("admin.manage_profiles_tip"))

        self._editor_box.setTitle(tr("admin.editor_group"))
        self._name_edit.setPlaceholderText(tr("admin.name_placeholder"))
        self._color_button.setText(tr("admin.pick_color"))
        self._icon_combo.clear()
        for name in icons.GLYPH_NAMES:
            self._icon_combo.addItem(
                icons.glyph_pixmap(name, "#e7eaf0", 16),
                tr(f"icon.{name}"),
                name,
            )
        self._image_button.setText(tr("admin.pick_image"))
        self._image_button.setToolTip(tr("admin.image_tip"))
        self._image_clear.setText(tr("admin.clear_image"))
        self._favorite_check.setText(tr("admin.favorite"))
        self._move_up.setText(tr("admin.up"))
        self._move_down.setText(tr("admin.down"))
        self._open_button.setText(tr("admin.open"))
        self._reset_button.setText(tr("admin.reset"))
        self._reset_button.setToolTip(tr("admin.reset_tip"))

        self._settings_box.setTitle(tr("admin.settings_group"))
        self._poll_spin.setSuffix(" ms")
        self._activate_check.setText(tr("admin.settings.activate_on_click"))
        self._hotkeys_check.setText(tr("admin.settings.hotkeys"))
        self._autostart_check.setText(tr("admin.settings.autostart"))
        self._tabs_check.setText(tr("admin.settings.read_tabs"))
        self._tabs_check.setToolTip(tr("admin.settings.read_tabs_tip"))

        self._shortcuts_box.setTitle(tr("admin.shortcuts_group"))
        self._shortcut_table.setHorizontalHeaderLabels(
            [tr("admin.shortcuts.action"), tr("admin.shortcuts.shortcut")]
        )
        self._shortcut_note.setText(tr("admin.shortcuts.note"))
        self._shortcut_reset.setText(tr("admin.shortcuts.reset"))

        self.set_shortcuts(self._shortcut_bindings)
        self._load_editor(self._profile_by_id(self._current) if self._current else None)
        self._loading = previous

    # ------------------------------------------------------------- actions

    def _profile_by_id(self, profile_id: str) -> Profile | None:
        return next((p for p in self._profiles if p.id == profile_id), None)

    def _load_editor(self, profile: Profile | None) -> None:
        previous = self._loading
        self._loading = True
        enabled = profile is not None
        for widget in (
            self._name_edit,
            self._color_button,
            self._icon_combo,
            self._favorite_check,
            self._image_button,
            self._image_clear,
        ):
            widget.setEnabled(enabled)
        if profile is None:
            self._name_edit.setText("")
            self._image_preview.clear()
            self._loading = previous
            return
        self._current = profile.id
        self._name_edit.setText(profile.display_name)
        self._favorite_check.setChecked(profile.is_favorite)
        index = self._icon_combo.findData(profile.icon)
        self._icon_combo.setCurrentIndex(max(0, index))
        self._color_preview.setStyleSheet(f"background-color: {profile.color}; border-radius: 6px;")
        if profile.custom_image:
            pixmap = icons.avatar_pixmap(profile, 40)
            self._image_preview.setPixmap(pixmap)
        else:
            self._image_preview.clear()
        self._loading = previous

    def _on_table_selection(self) -> None:
        if self._loading:
            return
        row = self._table.currentRow()
        if row < 0:
            return
        item = self._table.item(row, 0)
        if item is None:
            return
        profile_id = item.data(Qt.UserRole)
        self._current = profile_id
        self._load_editor(self._profile_by_id(profile_id))
        self.selectionChanged.emit(profile_id)

    def _on_rename(self) -> None:
        if self._loading or not self._current:
            return
        self.renameRequested.emit(self._current, self._name_edit.text())

    def _on_pick_color(self) -> None:
        if not self._current:
            return
        profile = self._profile_by_id(self._current)
        if profile is None:
            return
        chosen = QColorDialog.getColor(QColor(profile.color), self, tr("dialog.color.title"))
        if chosen.isValid():
            self._color_preview.setStyleSheet(
                f"background-color: {chosen.name()}; border-radius: 6px;"
            )
            self.colorRequested.emit(self._current, chosen.name())

    def _on_icon_changed(self, _index: int) -> None:
        if self._loading or not self._current:
            return
        name = self._icon_combo.currentData()
        if name:
            self.iconRequested.emit(self._current, str(name))

    def _on_favorite_toggled(self, state: bool) -> None:
        if self._loading or not self._current:
            return
        self.favoriteToggled.emit(self._current, state)

    def _on_shortcut_edited(self, item: QTableWidgetItem) -> None:
        if self._loading or item.column() != 1:
            return
        action = SHORTCUT_ACTIONS[item.row()][0]
        self.shortcutChanged.emit(action, item.text().strip())

    def _emit_move(self, delta: int) -> None:
        if self._current:
            self.moveRequested.emit(self._current, delta)

    def _emit_open(self) -> None:
        if self._current:
            self.openProfileRequested.emit(self._current)

    def _emit_reset(self) -> None:
        if self._current:
            self.resetRequested.emit(self._current)

    def _emit_image(self) -> None:
        if self._current:
            self.imageRequested.emit(self._current)

    def _emit_clear_image(self) -> None:
        if self._current:
            self.imageCleared.emit(self._current)

    @property
    def _shortcut_bindings(self) -> dict[str, str]:
        return {
            action: self._shortcut_table.item(row, 1).text()
            for row, (action, _) in enumerate(SHORTCUT_ACTIONS)
            if self._shortcut_table.item(row, 1) is not None
        }


def _label_key(action: str) -> str:
    """Translation key of a shortcut action."""
    for name, key in SHORTCUT_ACTIONS:
        if name == action:
            return key
    return action
