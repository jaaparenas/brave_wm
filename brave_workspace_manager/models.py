"""Data models shared by the logic and the interface."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from .i18n import tr


class MatchMethod(str, Enum):
    """How the owning profile of a window was determined."""

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
    custom_image: str = ""
    active_time: float | None = None
    custom: bool = False
    is_virtual: bool = False

    @property
    def label(self) -> str:
        return self.display_name or self.brave_display_name or self.directory_name

    @property
    def status_text(self) -> str:
        if not self.is_open:
            return tr("card.status.closed")
        windows = (
            tr("card.windows.one")
            if self.window_count == 1
            else tr("card.windows.many", count=self.window_count)
        )
        if self.tab_count:
            tabs = (
                tr("card.tabs.one")
                if self.tab_count == 1
                else tr("card.tabs.many", count=self.tab_count)
            )
            return tr("card.status.open", windows=windows, tabs=tabs)
        return tr("card.status.open_no_tabs", windows=windows)


@dataclass(slots=True)
class WindowInfo:
    window_id: int
    pid: int
    title: str = ""
    wm_class: str = ""
    is_active: bool = False
    is_minimized: bool = False
    is_maximized: bool = False
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
            return tr("window.state.active")
        if self.is_minimized:
            return tr("window.state.minimized")
        return tr("window.state.background")

    @property
    def tabs_text(self) -> str:
        if not self.tab_count:
            return ""
        return (
            tr("card.tabs.one")
            if self.tab_count == 1
            else tr("card.tabs.many", count=self.tab_count)
        )


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
