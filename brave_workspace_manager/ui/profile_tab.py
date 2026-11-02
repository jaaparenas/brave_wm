"""Profile card shown in the gallery."""

from __future__ import annotations

from PySide6.QtCore import QMimeData, QPoint, QSize, Qt, Signal
from PySide6.QtGui import QDrag, QFontMetrics, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMenu,
    QSizePolicy,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from ..i18n import tr
from ..models import Profile, WindowInfo
from . import icons
from .theme import ACCENT, BORDER, SURFACE, SURFACE_ALT, TEXT, TEXT_MUTED

MIME_TYPE = "application/x-brave-workspace-profile"
ACTION_ACTIONS = ("activate", "minimize", "maximize", "close")


class ProfileTab(QFrame):
    """Card of a profile inside the gallery."""

    activated = Signal(str)
    contextRequested = Signal(str, QPoint)
    doubleClicked = Signal(str)
    windowActionRequested = Signal(str, int, str)

    WIDTH = 168
    HEIGHT = 176
    AVATAR = 48
    BUTTON = 26

    def __init__(self, profile: Profile, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.profile_id = profile.id
        self.setObjectName("Card")
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumHeight(self.HEIGHT)
        self._selected = False
        self._profile: Profile = profile
        self._windows: list[WindowInfo] = []
        self._press_pos: QPoint | None = None
        self._dragging = False

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

        self._tabs = QLabel()
        self._tabs.setAlignment(Qt.AlignCenter)
        self._tabs.setObjectName("Muted")
        self._tabs.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        layout.addWidget(self._tabs)

        layout.addStretch(1)
        layout.addLayout(self._build_actions())
        self.update_profile(profile)

    # ------------------------------------------------------------- building

    def _build_actions(self) -> QHBoxLayout:
        """Row of small buttons that act on the windows of the profile."""
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(4)
        row.addStretch(1)
        self._buttons: dict[str, QToolButton] = {}
        for action in ACTION_ACTIONS:
            button = QToolButton()
            button.setFixedSize(self.BUTTON, self.BUTTON)
            button.setAutoRaise(True)
            button.setCursor(Qt.PointingHandCursor)
            button.setIconSize(QSize(self.BUTTON - 12, self.BUTTON - 12))
            button.clicked.connect(lambda _checked=False, a=action: self._emit_action(a))
            self._buttons[action] = button
            row.addWidget(button)
        self._more = QToolButton()
        self._more.setFixedSize(self.BUTTON, self.BUTTON)
        self._more.setAutoRaise(True)
        self._more.setIconSize(QSize(self.BUTTON - 12, self.BUTTON - 12))
        self._more.setCursor(Qt.PointingHandCursor)
        self._more.clicked.connect(self._show_window_menu)
        row.addWidget(self._more)
        row.addStretch(1)
        self._action_row = row
        return row

    # -------------------------------------------------------------- content

    def update_profile(self, profile: Profile) -> None:
        self.profile_id = profile.id
        self._profile = profile
        self._accent.setStyleSheet(f"background-color: {profile.color}; border-radius: 2px;")
        self._apply_style()
        self._avatar.setPixmap(icons.avatar_pixmap(profile, self.AVATAR))
        self._name.setToolTip(f"{profile.label}  ·  {profile.directory_name}")
        self._status.setObjectName("StatusOk" if profile.is_open else "StatusOff")
        if profile.is_favorite:
            self._favorite.setPixmap(icons.glyph_pixmap("star", "#ffd43b", 16))
        else:
            self._favorite.setPixmap(QPixmap())
        self._refresh_texts()

    def set_windows(self, windows: list[WindowInfo]) -> None:
        """Windows of this profile that the app knows about."""
        self._windows = list(windows)
        self._refresh_texts()

    def set_selected(self, selected: bool) -> None:
        """Marks the card as the active one in the gallery."""
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
            " border-radius: 10px; }"
            "QLabel { background: transparent; border: none; }"
        )

    def _refresh_texts(self) -> None:
        profile = self._profile
        self._set_elided(self._name, profile.label)
        self._set_elided(self._status, self._status_text())
        self._set_elided(self._tabs, self._tabs_text())
        self._refresh_buttons()
        self._refresh_tooltip()

    def _status_text(self) -> str:
        """Status without the tabs, which have their own line on the card."""
        profile = self._profile
        if not profile.is_open:
            return tr("card.status.closed")
        if profile.window_count == 1:
            windows = tr("card.windows.one")
        else:
            windows = tr("card.windows.many", count=profile.window_count)
        return tr("card.status.open_no_tabs", windows=windows)

    def _tabs_text(self) -> str:
        if not self._profile.is_open:
            return ""
        if self._profile.tab_count:
            if self._profile.tab_count == 1:
                return tr("card.tabs.one")
            return tr("card.tabs.many", count=self._profile.tab_count)
        return tr("card.tabs.unknown")

    def _refresh_tooltip(self) -> None:
        titles: list[str] = []
        for window in self._windows:
            etiqueta = window.title or tr("card.no_windows")
            if window.tab_titles:
                etiqueta = f"{etiqueta} — {window.tabs_text}"
            titles.append(etiqueta)
        if titles:
            self._tabs.setToolTip(tr("card.tabs.tooltip", titles="\n".join(titles)))
        else:
            self._tabs.setToolTip(tr("card.tabs.tooltip_empty"))

    def _refresh_buttons(self) -> None:
        """The buttons only work when the profile has a window."""
        ventana = self._primary_window()
        for button in self._buttons.values():
            button.setEnabled(ventana is not None)
            button.setVisible(ventana is not None)
        self._more.setEnabled(bool(self._windows))
        self._more.setVisible(len(self._windows) > 1)
        minimized = ventana is not None and ventana.is_minimized
        maximized = ventana is not None and ventana.is_maximized
        self._buttons["minimize"].setIcon(
            icons.action_pixmap("restore" if minimized else "minimize", TEXT, self.BUTTON - 12)
        )
        self._buttons["maximize"].setIcon(
            icons.action_pixmap("restore" if maximized else "maximize", TEXT, self.BUTTON - 12)
        )
        self._buttons["activate"].setIcon(icons.action_pixmap("activate", TEXT, self.BUTTON - 12))
        self._buttons["close"].setIcon(icons.action_pixmap("close", "#ff8787", self.BUTTON - 12))
        self._more.setIcon(icons.action_pixmap("more", TEXT_MUTED, self.BUTTON - 12))
        self._buttons["activate"].setToolTip(tr("card.action.activate"))
        self._buttons["minimize"].setToolTip(
            tr("card.action.restore") if minimized else tr("card.action.minimize")
        )
        self._buttons["maximize"].setToolTip(
            tr("card.action.unmaximize") if maximized else tr("card.action.maximize")
        )
        self._buttons["close"].setToolTip(tr("card.action.close_tip"))
        self._more.setToolTip(tr("card.menu.windows"))

    def _set_elided(self, label: QLabel, text: str) -> None:
        metrics = QFontMetrics(label.font())
        elided = metrics.elidedText(text, Qt.ElideRight, max(24, label.width()))
        if label.text() != elided:
            label.setText(elided)

    def resizeEvent(self, event) -> None:  # noqa: N802 (Qt API)
        super().resizeEvent(event)
        self._refresh_texts()

    # ----------------------------------------------------------- interaction

    def _primary_window(self) -> WindowInfo | None:
        """Window the buttons act on: the active one, or the first visible."""
        if not self._windows:
            return None
        for window in self._windows:
            if window.is_active:
                return window
        for window in self._windows:
            if not window.is_minimized:
                return window
        return self._windows[0]

    def _emit_action(self, action: str) -> None:
        ventana = self._primary_window()
        if ventana is None:
            return
        self.windowActionRequested.emit(self.profile_id, ventana.window_id, action)

    def _show_window_menu(self) -> None:
        """Menu with every window of the profile and its own actions."""
        if not self._windows:
            return
        menu = QMenu(self)
        menu.setTitle(tr("card.menu.windows"))
        for window in self._windows:
            titulo = window.title or tr("card.no_windows")
            if window.tab_titles:
                titulo = f"{titulo} — {window.tabs_text}"
            submenu = menu.addMenu(titulo)
            for action in ACTION_ACTIONS:
                if action == "minimize" and window.is_minimized:
                    etiqueta = tr("card.action.restore")
                elif action == "maximize" and window.is_maximized:
                    etiqueta = tr("card.action.unmaximize")
                else:
                    etiqueta = tr(f"card.action.{action}")
                submenu.addAction(etiqueta).triggered.connect(
                    lambda _checked=False, w=window, a=action: self._emit_window_action(w, a)
                )
        menu.exec(self.cursor().pos())

    def _emit_window_action(self, window: WindowInfo, action: str) -> None:
        self.windowActionRequested.emit(self.profile_id, window.window_id, action)

    def mousePressEvent(self, event) -> None:  # noqa: N802 (Qt API)
        if event.button() == Qt.LeftButton:
            self._press_pos = event.position().toPoint()
            self._dragging = False
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:  # noqa: N802 (Qt API)
        if self._press_pos is not None and event.buttons() & Qt.LeftButton:
            distancia = (event.position().toPoint() - self._press_pos).manhattanLength()
            if distancia >= QApplication.startDragDistance():
                self._start_drag()
                return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802 (Qt API)
        if event.button() == Qt.LeftButton:
            self._press_pos = None
            if not self._dragging:
                self.activated.emit(self.profile_id)
            self._dragging = False
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event) -> None:  # noqa: N802 (Qt API)
        self.doubleClicked.emit(self.profile_id)
        super().mouseDoubleClickEvent(event)

    def contextMenuEvent(self, event) -> None:  # noqa: N802 (Qt API)
        self.contextRequested.emit(self.profile_id, event.globalPos())
        super().contextMenuEvent(event)

    def _start_drag(self) -> None:
        """Starts the drag that reorders the cards of the gallery."""
        self._dragging = True
        mime = QMimeData()
        mime.setData(MIME_TYPE, self.profile_id.encode("utf-8"))
        drag = QDrag(self)
        drag.setMimeData(mime)
        drag.setPixmap(self.grab())
        drag.exec(Qt.MoveAction)
