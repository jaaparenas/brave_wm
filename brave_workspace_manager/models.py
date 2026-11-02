"""Modelos de datos compartidos entre la logica y la interfaz."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class MatchMethod(str, Enum):
    """Como se determino el perfil propietario de una ventana."""

    LEARNED = "learned"
    MANUAL = "manual"
    SINGLE_PROFILE = "single-profile"
    TITLE = "title"
    ELIMINATION = "elimination"
    NONE = "unassigned"


@dataclass(slots=True)
class Profile:
    id: str
    directory_name: str
    display_name: str = ""
    brave_display_name: str = ""
    color: str = "#4f8cff"
    icon: str = "circle"
    sort_order: int = 0
    is_favorite: bool = False
    is_open: bool = False
    window_count: int = 0
    tab_count: int = 0
    avatar_path: str | None = None
    active_time: float | None = None
    custom: bool = False

    @property
    def label(self) -> str:
        return self.display_name or self.brave_display_name or self.directory_name

    @property
    def status_text(self) -> str:
        if not self.is_open:
            return "Cerrado"
        ventanas = "1 ventana" if self.window_count == 1 else f"{self.window_count} ventanas"
        if self.tab_count:
            pestanas = "1 pestaña" if self.tab_count == 1 else f"{self.tab_count} pestañas"
            return f"Abierto · {ventanas} · {pestanas}"
        return f"Abierto · {ventanas}"


@dataclass(slots=True)
class WindowInfo:
    window_id: int
    pid: int
    title: str = ""
    wm_class: str = ""
    is_active: bool = False
    is_minimized: bool = False
    profile_id: str | None = None
    method: MatchMethod = MatchMethod.NONE
    confidence: float = 0.0
    x: int = 0
    y: int = 0
    width: int = 0
    height: int = 0
    tab_count: int = 0
    tab_titles: list[str] = field(default_factory=list)
    active_tab: int = -1

    @property
    def state_text(self) -> str:
        if self.is_active:
            return "Activa"
        if self.is_minimized:
            return "Minimizada"
        return "En segundo plano"

    @property
    def tabs_text(self) -> str:
        if not self.tab_count:
            return ""
        return "1 pestaña" if self.tab_count == 1 else f"{self.tab_count} pestañas"


@dataclass(slots=True)
class BrowserProcess:
    pid: int
    ppid: int = 0
    kind: str = "browser"
    cmdline: list[str] = field(default_factory=list)
    profile_directory: str | None = None
    user_data_dir: str | None = None

    @property
    def is_browser_process(self) -> bool:
        return self.kind == "browser"
