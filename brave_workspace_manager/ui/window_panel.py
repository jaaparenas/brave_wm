"""Panel que muestra las ventanas de Brave asociadas al perfil seleccionado."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from ..models import Profile, WindowInfo


class WindowCard(QFrame):
    """Tarjeta con los datos de una ventana de Brave."""

    activateRequested = Signal(int)
    toggleRequested = Signal(int)
    assignRequested = Signal(int, str)

    def __init__(
        self,
        window: WindowInfo,
        profiles: list[Profile],
        assignable: bool = False,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("Card")
        self.window_id = window.window_id
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(6)

        title = QLabel(self._elide(window.title) or "(sin titulo)")
        title.setToolTip(window.title or "Ventana de Brave")
        title.setStyleSheet("font-weight: 600;")
        layout.addWidget(title)

        meta = QLabel(f"Ventana 0x{window.window_id:x} · PID {window.pid} · {window.state_text}")
        meta.setObjectName("Muted")
        layout.addWidget(meta)

        if window.tab_count:
            self._add_tabs(layout, window)
        else:
            activa = QLabel("Solo se ve la pestaña activa de esta ventana.")
            activa.setObjectName("Muted")
            layout.addWidget(activa)

        actions = QHBoxLayout()
        actions.setSpacing(8)
        actions.addStretch(1)

        if assignable:
            combo = QComboBox()
            combo.setMinimumWidth(180)
            combo.addItem("Asignar a un perfil…", "")
            for profile in profiles:
                combo.addItem(profile.label, profile.id)
            combo.currentIndexChanged.connect(self._on_assign)
            actions.addWidget(combo)

        toggle = QPushButton("Restaurar" if window.is_minimized else "Minimizar")
        toggle.clicked.connect(lambda: self.toggleRequested.emit(self.window_id))
        actions.addWidget(toggle)

        activate = QPushButton("Activar")
        activate.setObjectName("Primary")
        activate.clicked.connect(lambda: self.activateRequested.emit(self.window_id))
        actions.addWidget(activate)

        layout.addLayout(actions)

    def _elide(self, text: str) -> str:
        return self.fontMetrics().elidedText(text, Qt.ElideRight, 420)

    def _add_tabs(self, layout: QVBoxLayout, window: WindowInfo) -> None:
        """Boton con el numero de pestanas y la lista desplegable de titulos."""
        boton = QToolButton()
        boton.setText(window.tabs_text)
        boton.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        boton.setArrowType(Qt.DownArrow)
        boton.setCheckable(True)
        boton.setAutoRaise(True)
        boton.setToolTip("Pestañas abiertas en esta ventana:\n" + "\n".join(window.tab_titles))

        lista = QWidget()
        lista_layout = QVBoxLayout(lista)
        lista_layout.setContentsMargins(12, 2, 0, 0)
        lista_layout.setSpacing(2)
        for indice, titulo in enumerate(window.tab_titles):
            es_activa = indice == window.active_tab
            etiqueta = QLabel(self._elide(titulo) or "(sin titulo)")
            etiqueta.setToolTip(titulo)
            if es_activa:
                etiqueta.setText("▸ " + etiqueta.text())
                etiqueta.setStyleSheet("font-weight: 600;")
            else:
                etiqueta.setObjectName("Muted")
            lista_layout.addWidget(etiqueta)
        lista.setVisible(False)
        boton.toggled.connect(lista.setVisible)

        layout.addWidget(boton)
        layout.addWidget(lista)

    def _on_assign(self, index: int) -> None:
        combo = self.findChild(QComboBox)
        if combo is None:
            return
        profile_id = combo.itemData(index)
        if profile_id:
            self.assignRequested.emit(self.window_id, profile_id)


class WindowPanel(QWidget):
    """Lista de ventanas del perfil activo y de ventanas sin asignar."""

    windowActivated = Signal(int)
    windowToggled = Signal(int)
    windowAssigned = Signal(int, str)
    adoptRequested = Signal(str)
    openProfileRequested = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._profile: Profile | None = None

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(10)

        header = QHBoxLayout()
        self._title = QLabel("Selecciona un perfil")
        self._title.setStyleSheet("font-weight: 600; font-size: 15px;")
        header.addWidget(self._title)
        header.addStretch(1)

        self._adopt_button = QPushButton("Tomar la ventana activa")
        self._adopt_button.setToolTip(
            "Asigna a este perfil la ventana de Brave que tenga el foco ahora mismo"
        )
        self._adopt_button.clicked.connect(self._emit_adopt)
        header.addWidget(self._adopt_button)

        self._open_button = QPushButton("Abrir perfil")
        self._open_button.setObjectName("Primary")
        self._open_button.clicked.connect(self._emit_open)
        header.addWidget(self._open_button)
        root.addLayout(header)

        self._tabs_note = QLabel()
        self._tabs_note.setObjectName("Muted")
        self._tabs_note.setWordWrap(True)
        self._tabs_note.setVisible(False)
        root.addWidget(self._tabs_note)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._container = QWidget()
        self._container_layout = QVBoxLayout(self._container)
        self._container_layout.setContentsMargins(0, 0, 6, 0)
        self._container_layout.setSpacing(16)
        self._windows_layout = QVBoxLayout()
        self._windows_layout.setContentsMargins(0, 0, 0, 0)
        self._windows_layout.setSpacing(10)
        self._unassigned_layout = QVBoxLayout()
        self._unassigned_layout.setContentsMargins(0, 0, 0, 0)
        self._unassigned_layout.setSpacing(10)
        self._container_layout.addLayout(self._windows_layout)
        self._container_layout.addLayout(self._unassigned_layout)
        self._container_layout.addStretch(1)
        self._scroll.setWidget(self._container)
        root.addWidget(self._scroll, 1)

    # ------------------------------------------------------------- contenido

    def set_profile(self, profile: Profile | None) -> None:
        self._profile = profile
        if profile is None:
            self._title.setText("Selecciona un perfil")
            self._adopt_button.setEnabled(False)
            self._open_button.setEnabled(False)
        else:
            self._title.setText(f"Ventanas de {profile.label}")
            self._adopt_button.setEnabled(True)
            self._open_button.setEnabled(True)

    def set_tabs_status(self, text: str) -> None:
        """Aviso sobre la lectura de pestanas (por que no aparece el numero)."""
        self._tabs_note.setText(text)
        self._tabs_note.setVisible(bool(text))

    def set_windows(self, windows: list[WindowInfo], profiles: list[Profile]) -> None:
        self._clear(self._windows_layout)
        if not windows:
            self._add_note(
                self._windows_layout,
                "Este perfil no tiene ventanas abiertas. "
                "Pulsa «Abrir perfil» para iniciarlo en su directorio nativo.",
            )
        for window in windows:
            card = WindowCard(window, profiles, assignable=False)
            card.activateRequested.connect(self.windowActivated.emit)
            card.toggleRequested.connect(self.windowToggled.emit)
            self._windows_layout.addWidget(card)

    def set_unassigned(self, windows: list[WindowInfo], profiles: list[Profile]) -> None:
        self._clear(self._unassigned_layout)
        if not windows:
            return
        heading = QLabel(f"Ventanas sin asignar ({len(windows)})")
        heading.setStyleSheet("font-weight: 600; color: #ffd43b;")
        self._unassigned_layout.addWidget(heading)
        note = QLabel(
            "Chromium no expone a que perfil pertenece cada ventana. "
            "Asignalas manualmente o se detectaran solas en cuanto se repitan."
        )
        note.setObjectName("Muted")
        note.setWordWrap(True)
        self._unassigned_layout.addWidget(note)
        for window in windows:
            card = WindowCard(window, profiles, assignable=True)
            card.activateRequested.connect(self.windowActivated.emit)
            card.toggleRequested.connect(self.windowToggled.emit)
            card.assignRequested.connect(self.windowAssigned.emit)
            self._unassigned_layout.addWidget(card)

    # ------------------------------------------------------------- auxiliares

    @staticmethod
    def _clear(layout) -> None:
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

    def _add_note(self, layout, text: str) -> None:
        note = QLabel(text)
        note.setObjectName("Muted")
        note.setWordWrap(True)
        layout.addWidget(note)

    def _emit_adopt(self) -> None:
        if self._profile is not None:
            self.adoptRequested.emit(self._profile.id)

    def _emit_open(self) -> None:
        if self._profile is not None:
            self.openProfileRequested.emit(self._profile.id)
