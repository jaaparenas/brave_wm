"""Panel de administracion: perfiles, personalizacion, atajos y ajustes."""

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

from ..models import Profile
from . import icons

SHORTCUT_ACTIONS = (
    ("profile-1", "Activar perfil 1"),
    ("profile-2", "Activar perfil 2"),
    ("profile-3", "Activar perfil 3"),
    ("profile-4", "Activar perfil 4"),
    ("profile-5", "Activar perfil 5"),
    ("profile-6", "Activar perfil 6"),
    ("profile-7", "Activar perfil 7"),
    ("profile-8", "Activar perfil 8"),
    ("profile-9", "Activar perfil 9"),
    ("next-profile", "Perfil siguiente"),
    ("prev-profile", "Perfil anterior"),
    ("toggle-admin", "Mostrar u ocultar el administrador"),
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
    "toggle-admin": "Ctrl+Alt+B",
}

ICON_LABELS = {
    "circle": "Circulo",
    "star": "Estrella",
    "heart": "Corazon",
    "bolt": "Rayo",
    "globe": "Globo",
    "code": "Codigo",
    "briefcase": "Maletin",
    "home": "Casa",
    "book": "Libro",
    "gear": "Engranaje",
    "leaf": "Hoja",
    "flame": "Llama",
    "sun": "Sol",
    "moon": "Luna",
    "user": "Persona",
    "folder": "Carpeta",
}


class AdminPanel(QWidget):
    """Edicion de perfiles y configuracion general."""

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

    # ------------------------------------------------------------- construccion

    def _build_profiles_group(self) -> QWidget:
        box = QGroupBox("Perfiles detectados")
        box.setObjectName("Card")
        layout = QVBoxLayout(box)
        layout.setContentsMargins(12, 12, 12, 12)

        self._table = QTableWidget(0, 4)
        self._table.setHorizontalHeaderLabels(["Perfil", "Carpeta", "Estado", "Ventanas"])
        self._table.verticalHeader().setVisible(False)
        self._table.setSelectionBehavior(QTableWidget.SelectRows)
        self._table.setSelectionMode(QTableWidget.SingleSelection)
        self._table.setEditTriggers(QTableWidget.NoEditTriggers)
        header = self._table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self._table.setMinimumHeight(220)
        self._table.itemSelectionChanged.connect(self._on_table_selection)
        layout.addWidget(self._table)

        buttons = QHBoxLayout()
        manage = QPushButton("Gestor de perfiles de Brave")
        manage.setToolTip(
            "Abre el gestor nativo de Brave; la aplicacion no escribe en sus bases de datos"
        )
        manage.clicked.connect(self.manageProfilesRequested.emit)
        buttons.addWidget(manage)
        buttons.addStretch(1)
        layout.addLayout(buttons)
        return box

    def _build_editor_group(self) -> QWidget:
        box = QGroupBox("Personalizacion del perfil")
        box.setObjectName("Card")
        layout = QVBoxLayout(box)
        layout.setContentsMargins(12, 12, 12, 12)

        form = QFormLayout()
        form.setSpacing(10)

        self._name_edit = QLineEdit()
        self._name_edit.setPlaceholderText("Nombre visible (vacio = el de Brave)")
        self._name_edit.editingFinished.connect(self._on_rename)
        form.addRow("Nombre", self._name_edit)

        color_row = QHBoxLayout()
        self._color_button = QPushButton("Elegir color")
        self._color_button.clicked.connect(self._on_pick_color)
        color_row.addWidget(self._color_button)
        self._color_preview = QFrame()
        self._color_preview.setFixedSize(28, 20)
        color_row.addWidget(self._color_preview)
        color_row.addStretch(1)
        form.addRow("Color", color_row)

        self._icon_combo = QComboBox()
        for name in icons.GLYPH_NAMES:
            self._icon_combo.addItem(
                icons.glyph_pixmap(name, "#e7eaf0", 16),
                ICON_LABELS.get(name, name.capitalize()),
                name,
            )
        self._icon_combo.currentIndexChanged.connect(self._on_icon_changed)
        form.addRow("Icono", self._icon_combo)

        self._favorite_check = QCheckBox("Marcar como favorito")
        self._favorite_check.toggled.connect(self._on_favorite_toggled)
        form.addRow("", self._favorite_check)
        layout.addLayout(form)

        buttons = QHBoxLayout()
        move_up = QPushButton("Subir")
        move_up.clicked.connect(lambda: self._emit_move(-1))
        buttons.addWidget(move_up)
        move_down = QPushButton("Bajar")
        move_down.clicked.connect(lambda: self._emit_move(1))
        buttons.addWidget(move_down)
        open_button = QPushButton("Abrir perfil")
        open_button.clicked.connect(self._emit_open)
        buttons.addWidget(open_button)
        reset = QPushButton("Restablecer")
        reset.setToolTip("Vuelve al nombre y al icono originales de Brave")
        reset.clicked.connect(self._emit_reset)
        buttons.addWidget(reset)
        buttons.addStretch(1)
        layout.addLayout(buttons)
        return box

    def _build_settings_group(self) -> QWidget:
        box = QGroupBox("Ajustes")
        box.setObjectName("Card")
        layout = QVBoxLayout(box)
        layout.setContentsMargins(12, 12, 12, 12)

        form = QFormLayout()
        form.setSpacing(10)

        self._poll_spin = QSpinBox()
        self._poll_spin.setRange(500, 30000)
        self._poll_spin.setSingleStep(500)
        self._poll_spin.setSuffix(" ms")
        self._poll_spin.valueChanged.connect(
            lambda value: self.settingChanged.emit("poll_interval", str(value))
        )
        form.addRow("Actualizar cada", self._poll_spin)

        self._activate_check = QCheckBox("Activar el perfil al hacer clic")
        self._activate_check.toggled.connect(
            lambda state: self.settingChanged.emit("activate_on_click", "1" if state else "0")
        )
        form.addRow("", self._activate_check)

        self._hotkeys_check = QCheckBox("Atajos globales de teclado")
        self._hotkeys_check.toggled.connect(
            lambda state: self.settingChanged.emit("hotkeys_enabled", "1" if state else "0")
        )
        form.addRow("", self._hotkeys_check)

        self._tray_check = QCheckBox("Icono en la bandeja del sistema")
        self._tray_check.toggled.connect(
            lambda state: self.settingChanged.emit("tray_enabled", "1" if state else "0")
        )
        form.addRow("", self._tray_check)

        self._autostart_check = QCheckBox("Iniciar con el sistema")
        self._autostart_check.toggled.connect(
            lambda state: self.settingChanged.emit("autostart", "1" if state else "0")
        )
        form.addRow("", self._autostart_check)

        layout.addLayout(form)
        return box

    def _build_shortcuts_group(self) -> QWidget:
        box = QGroupBox("Atajos de teclado")
        box.setObjectName("Card")
        layout = QVBoxLayout(box)
        layout.setContentsMargins(12, 12, 12, 12)

        self._shortcut_table = QTableWidget(0, 2)
        self._shortcut_table.setHorizontalHeaderLabels(["Accion", "Atajo"])
        self._shortcut_table.verticalHeader().setVisible(False)
        self._shortcut_table.setEditTriggers(QTableWidget.DoubleClicked)
        self._shortcut_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self._shortcut_table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeToContents
        )
        self._shortcut_table.itemChanged.connect(self._on_shortcut_edited)
        layout.addWidget(self._shortcut_table)

        note = QLabel(
            "Los atajos globales se reservan en el servidor X. Si Cinnamon ya usa "
            "una combinacion, la aplicacion lo indica y no la roba."
        )
        note.setObjectName("Muted")
        note.setWordWrap(True)
        layout.addWidget(note)

        reset = QPushButton("Restablecer atajos")
        reset.clicked.connect(self.shortcutResetRequested.emit)
        layout.addWidget(reset)
        return box

    # ------------------------------------------------------------- datos

    def set_profiles(self, profiles: list[Profile]) -> None:
        self._profiles = profiles
        self._loading = True
        self._table.setRowCount(len(profiles))
        for row, profile in enumerate(profiles):
            name_item = QTableWidgetItem(profile.label)
            name_item.setData(Qt.UserRole, profile.id)
            self._table.setItem(row, 0, name_item)
            self._table.setItem(row, 1, QTableWidgetItem(profile.directory_name))
            self._table.setItem(row, 2, QTableWidgetItem(profile.status_text))
            self._table.setItem(row, 3, QTableWidgetItem(str(profile.window_count)))
        if profiles:
            index = next((i for i, p in enumerate(profiles) if p.id == self._current), 0)
            self._table.selectRow(index)
            self._load_editor(profiles[index])
        else:
            self._load_editor(None)
        self._loading = False

    def set_shortcuts(self, bindings: dict[str, str]) -> None:
        self._loading = True
        self._shortcut_table.setRowCount(len(SHORTCUT_ACTIONS))
        for row, (action, label) in enumerate(SHORTCUT_ACTIONS):
            name_item = QTableWidgetItem(label)
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
        self._tray_check.setChecked(
            settings.get("tray_enabled", "0") == "0" or settings.get("tray_enabled", "1") == "1"
        )
        self._autostart_check.setChecked(settings.get("autostart", "0") == "1")
        self._loading = False

    def select_profile(self, profile_id: str) -> None:
        self._current = profile_id
        for row in range(self._table.rowCount()):
            item = self._table.item(row, 0)
            if item is not None and item.data(Qt.UserRole) == profile_id:
                self._table.selectRow(row)
                self._load_editor(self._profile_by_id(profile_id))
                return

    # ------------------------------------------------------------- acciones

    def _profile_by_id(self, profile_id: str) -> Profile | None:
        return next((p for p in self._profiles if p.id == profile_id), None)

    def _load_editor(self, profile: Profile | None) -> None:
        self._loading = True
        enabled = profile is not None
        for widget in (
            self._name_edit,
            self._color_button,
            self._icon_combo,
            self._favorite_check,
        ):
            widget.setEnabled(enabled)
        if profile is None:
            self._name_edit.setText("")
            return
        self._current = profile.id
        self._name_edit.setText(profile.display_name)
        self._favorite_check.setChecked(profile.is_favorite)
        index = self._icon_combo.findData(profile.icon)
        self._icon_combo.setCurrentIndex(max(0, index))
        self._color_preview.setStyleSheet(f"background-color: {profile.color}; border-radius: 6px;")
        self._loading = False

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
        chosen = QColorDialog.getColor(QColor(profile.color), self, "Color del perfil")
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
