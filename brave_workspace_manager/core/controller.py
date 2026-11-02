"""Controller: coordinates profile discovery, windows and actions."""

from __future__ import annotations

import contextlib
import os
import shutil
import time
from pathlib import Path

from PySide6.QtCore import QObject, QThread, QTimer, Signal

from .. import discovery, processes
from ..a11y_switch import A11ySwitch
from ..config import brave_user_data_dir, data_dir
from ..database import Database
from ..i18n import tr
from ..models import MatchMethod, Profile, WindowInfo
from ..tabs import FrameTabs, TabReader, emparejar
from ..x11.base import WindowBackend
from .launcher import ProfileLauncher
from .resolver import ResolutionContext, WindowResolver

PROFILE_PALETTE = (
    "#4f8cff",
    "#ff6b6b",
    "#51cf66",
    "#ffd43b",
    "#cc5de8",
    "#20c997",
    "#ff922b",
    "#339af0",
    "#f06595",
    "#94d82d",
)

LAUNCH_LEARNING_SECONDS = 20.0
TAB_INTERVAL_SECONDS = 10.0
A11Y_PULSE_SECONDS = 12.0
A11Y_RETRY_SECONDS = 300.0
IMAGE_EXTENSIONS = (".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif")


class TabReaderThread(QThread):
    """Reads the tabs of Brave outside of the interface thread."""

    tabsRead = Signal(list)

    def __init__(self, reader: TabReader) -> None:
        super().__init__()
        self._reader = reader

    def run(self) -> None:  # pragma: no cover - depends on the environment
        try:
            frames = self._reader.read()
        except Exception:
            frames = []
        self.tabsRead.emit(frames)


class AppController(QObject):
    """Shared state of the application."""

    profilesChanged = Signal()
    windowsChanged = Signal()
    statusMessage = Signal(str)
    selectionChanged = Signal(str)
    profileActivated = Signal(str)

    def __init__(
        self,
        database: Database,
        backend: WindowBackend,
        launcher: ProfileLauncher,
        user_data_dir: Path | None = None,
        tab_reader: object | None = None,
        a11y_switch: object | None = None,
    ) -> None:
        super().__init__()
        self.database = database
        self.backend = backend
        self.launcher = launcher
        self.user_data_dir = Path(user_data_dir or brave_user_data_dir())
        self.resolver = WindowResolver()
        self.profiles: list[Profile] = []
        self.windows: list[WindowInfo] = []
        self.selected_profile_id: str | None = None
        self.poll_interval_ms = 2000
        self._timer: QTimer | None = None
        self._launch_target: str | None = None
        self._launch_deadline = 0.0
        self._baseline_window_ids: set[int] = set()
        self.tab_reader = tab_reader or TabReader()
        self.a11y_switch = a11y_switch or A11ySwitch()
        self._needs_a11y = False
        self._a11y_failed = False
        self._last_pulse = -A11Y_RETRY_SECONDS
        self._pulse_restore: bool | None = None
        self._frames: list[FrameTabs] = []
        self._tab_thread: TabReaderThread | None = None
        self._last_tab_read = 0.0
        self._leer_pestanas = True
        self._navegador_abierto = False
        self._detached: dict[tuple[int, int], str | None] = {}
        self._open_dirs: set[str] = set()

    # ------------------------------------------------------------ life cycle

    def start(self) -> None:
        self.refresh()
        self._timer = QTimer(self)
        self._timer.setInterval(self.poll_interval_ms)
        self._timer.timeout.connect(self.refresh)
        self._timer.start()

    def stop(self) -> None:
        if self._timer is not None:
            self._timer.stop()
            self._timer = None
        if self._tab_thread is not None:
            self._tab_thread.wait(3000)
            self._tab_thread = None
        self._end_a11y_pulse()

    def set_poll_interval(self, milliseconds: int) -> None:
        self.poll_interval_ms = max(500, int(milliseconds))
        if self._timer is not None:
            self._timer.setInterval(self.poll_interval_ms)

    # ----------------------------------------------------------------- state

    def profile(self, profile_id: str) -> Profile | None:
        return next((p for p in self.profiles if p.id == profile_id), None)

    def profile_by_directory(self, directory_name: str) -> Profile | None:
        return next((p for p in self.profiles if p.directory_name == directory_name), None)

    def windows_for(self, profile_id: str | None) -> list[WindowInfo]:
        if profile_id is None:
            return []
        return [w for w in self.windows if w.profile_id == profile_id]

    def unassigned_windows(self) -> list[WindowInfo]:
        return [w for w in self.windows if not w.profile_id]

    @property
    def tabs_status(self) -> str:
        """Notice about the tab reading; empty when everything works."""
        if not self._leer_pestanas:
            return ""
        motivo = self.tab_reader.motivo
        if motivo:
            return tr("tabs.unreadable", reason=motivo)
        if self._a11y_failed and self._needs_a11y:
            return tr("tabs.no_accessibility")
        return ""

    def set_read_tabs(self, enabled: bool) -> None:
        """Turns the tab reading and the browser flag on or off."""
        self._leer_pestanas = bool(enabled)
        self.launcher.leer_pestanas = self._leer_pestanas
        if not self._leer_pestanas:
            self._frames = []
            self._aplicar_pestanas(self.windows, [])
        else:
            self._last_tab_read = 0.0
            self._programar_lectura_pestanas()

    def select(self, profile_id: str) -> None:
        self.selected_profile_id = profile_id
        self.selectionChanged.emit(profile_id)

    # ------------------------------------------------------------ refreshing

    def refresh(self) -> None:
        found = discovery.discover_profiles(self.user_data_dir)
        self.profiles = self._merge_profiles(found)

        process_list = processes.scan_brave_processes()
        browser_pids = [p.pid for p in processes.browser_processes(process_list)]
        self._navegador_abierto = bool(browser_pids)
        known_dirs = {p.directory_name for p in self.profiles}
        open_dirs = processes.profile_dirs_in_use(browser_pids, self.user_data_dir, known_dirs)

        windows = self._brave_windows(process_list)
        self._learn_from_launch(windows)

        assignments = self.database.load_assignments()
        context = ResolutionContext(
            profiles=self.profiles,
            windows=windows,
            open_profile_ids=open_dirs,
            assignments=assignments,
        )
        self.resolver.resolve(context)
        for window in windows:
            detached = (window.window_id, window.pid) in self._detached
            if detached and window.method not in (MatchMethod.LEARNED, MatchMethod.MANUAL):
                window.profile_id = None
                window.method = MatchMethod.NONE
                window.confidence = 0.0

        self._open_dirs = open_dirs
        self.windows = windows
        self._aplicar_pestanas(windows, self._frames)
        self._programar_lectura_pestanas()
        self.profilesChanged.emit()
        self.windowsChanged.emit()

    # ----------------------------------------------------------------- tabs

    def _aplicar_pestanas(self, windows: list[WindowInfo], frames: list[FrameTabs]) -> None:
        """Shares the tabs read between the windows and the profiles."""
        pares = emparejar(frames, windows) if frames else {}
        # Every Brave window has at least one tab: a frame without tabs means
        # that Brave is not publishing its interface tree.
        self._needs_a11y = any(frame.count == 0 for frame in pares.values())
        for window in windows:
            frame = pares.get(window.window_id)
            window.tab_count = frame.count if frame else 0
            window.tab_titles = list(frame.titles) if frame else []
            window.active_tab = frame.active if frame else -1
            if frame is not None:
                self._perfil_desde_marco(window, frame)
        for profile in self.profiles:
            profile.tab_count = sum(w.tab_count for w in windows if w.profile_id == profile.id)
            profile.window_count = sum(1 for w in windows if w.profile_id == profile.id)
            profile.is_open = profile.id in self._open_dirs or profile.window_count > 0

    def _perfil_desde_marco(self, window: WindowInfo, frame: FrameTabs) -> None:
        """Uses the profile name Brave publishes in the accessibility tree.

        It is the browser's own statement, so it beats learned assignments and
        guesses; only a manual assignment by the user is kept.
        """
        name = frame.profile_name.casefold()
        if not name or window.method == MatchMethod.MANUAL:
            return
        matches = [
            profile
            for profile in self.profiles
            if not profile.is_virtual and (profile.brave_display_name or "").casefold() == name
        ]
        if len(matches) != 1:
            return
        profile = matches[0]
        stored = window.method in (MatchMethod.LEARNED, MatchMethod.ACCESSIBILITY)
        if window.profile_id != profile.id or not stored:
            self.database.assign_window(
                window.window_id, window.pid, profile.id, window.title, "learned"
            )
        self._detached.pop((window.window_id, window.pid), None)
        window.profile_id = profile.id
        window.method = MatchMethod.ACCESSIBILITY
        window.confidence = 1.0

    def _programar_lectura_pestanas(self) -> None:
        if not self._leer_pestanas:
            return
        if self._tab_thread is not None and self._tab_thread.isRunning():
            return
        ahora = time.monotonic()
        if ahora - self._last_tab_read < TAB_INTERVAL_SECONDS:
            return
        self._last_tab_read = ahora
        if self._tab_thread is None:
            self._tab_thread = TabReaderThread(self.tab_reader)
            self._tab_thread.tabsRead.connect(self._on_tabs_read)
        self._tab_thread.start()

    def _on_tabs_read(self, frames: list) -> None:
        self._frames = frames
        self._aplicar_pestanas(self.windows, frames)
        if self._leer_pestanas and self._needs_a11y:
            self._start_a11y_pulse()
        elif not self._needs_a11y:
            self._a11y_failed = False
        self.profilesChanged.emit()
        self.windowsChanged.emit()

    def _start_a11y_pulse(self) -> None:
        """Asks Brave to build its accessibility tree, at most every few minutes."""
        if self._pulse_restore is not None:
            return
        now = time.monotonic()
        if now - self._last_pulse < A11Y_RETRY_SECONDS:
            # A pulse already ran and Brave still hides its tabs.
            self._a11y_failed = True
            return
        self._last_pulse = now
        previous = self.a11y_switch.get() if self.a11y_switch.available else None
        if previous is None or previous or not self.a11y_switch.set(True):
            self._a11y_failed = True
            return
        self._pulse_restore = previous
        QTimer.singleShot(int(A11Y_PULSE_SECONDS * 1000), self._finish_a11y_pulse)

    def _finish_a11y_pulse(self) -> None:
        self._end_a11y_pulse()
        self._last_tab_read = 0.0
        self._programar_lectura_pestanas()

    def _end_a11y_pulse(self) -> None:
        """Restores the bus property; Brave keeps its tree once it is built."""
        if self._pulse_restore is None:
            return
        self.a11y_switch.set(self._pulse_restore)
        self._pulse_restore = None

    def _merge_profiles(self, found: list[discovery.DiscoveredProfile]) -> list[Profile]:
        stored = self.database.load_profiles()
        merged: list[Profile] = []
        for index, item in enumerate(found):
            custom = stored.get(item.directory_name)
            if custom is not None:
                custom.brave_display_name = item.display_name
                custom.avatar_path = item.avatar_path
                custom.active_time = item.active_time
                custom.custom = True
                custom.is_virtual = False
                merged.append(custom)
                continue
            profile = Profile(
                id=item.directory_name,
                directory_name=item.directory_name,
                display_name="",
                brave_display_name=item.display_name,
                color=PROFILE_PALETTE[index % len(PROFILE_PALETTE)],
                icon="circle",
                sort_order=index,
                avatar_path=item.avatar_path,
                active_time=item.active_time,
            )
            self.database.save_profile(profile)
            merged.append(profile)

        for profile_id, profile in stored.items():
            if profile.is_virtual and profile_id not in {p.id for p in merged}:
                merged.append(profile)

        merged.sort(key=lambda p: (p.sort_order, p.id))
        return merged

    def _brave_windows(self, process_list: list[processes.BrowserProcess]) -> list[WindowInfo]:
        brave_pids = {p.pid for p in process_list}
        own_pid = os.getpid()
        windows = []
        for window in self.backend.list_windows():
            if window.pid == own_pid:
                continue
            tokens = window.wm_class.lower().replace("\0", " ").split()
            if window.pid in brave_pids or "brave-browser" in tokens:
                windows.append(window)
        return windows

    def _learn_from_launch(self, windows: list[WindowInfo]) -> None:
        if self._launch_target and time.monotonic() > self._launch_deadline:
            self._launch_target = None
            self._baseline_window_ids = set()
        if not self._launch_target:
            return
        new_windows = [
            window for window in windows if window.window_id not in self._baseline_window_ids
        ]
        if not new_windows:
            return
        active = [window for window in new_windows if window.is_active]
        if len(active) == 1:
            candidate = active[0]
        elif len(new_windows) == 1:
            candidate = new_windows[0]
        else:
            return
        self.database.assign_window(
            candidate.window_id, candidate.pid, self._launch_target, candidate.title, "learned"
        )
        candidate.profile_id = self._launch_target
        candidate.method = MatchMethod.LEARNED
        candidate.confidence = 1.0

    # --------------------------------------------------------------- actions

    def launch_profile(self, profile_id: str) -> bool:
        profile = self.profile(profile_id)
        if profile is None:
            return False
        if profile.is_virtual:
            self.statusMessage.emit(tr("status.virtual_profile"))
            return False
        if not self.launcher.available:
            self.statusMessage.emit(tr("status.brave_missing"))
            return False
        self._baseline_window_ids = {w.window_id for w in self.windows}
        self._launch_target = profile_id
        self._launch_deadline = time.monotonic() + LAUNCH_LEARNING_SECONDS
        if self.launcher.launch(profile.directory_name):
            self.statusMessage.emit(tr("status.opening", name=profile.label))
            return True
        self._launch_target = None
        self.statusMessage.emit(tr("status.launch_failed"))
        return False

    def activate_profile(self, profile_id: str) -> bool:
        profile = self.profile(profile_id)
        if profile is None:
            return False
        candidates = self.windows_for(profile_id)
        if candidates:
            candidates.sort(key=lambda w: (not w.is_active, w.is_minimized))
            target = candidates[0]
            if self.backend.activate(target.window_id):
                # Guesses (single profile, elimination) are not saved here: clicking a
                # card must not turn a wrong guess into a permanent assignment.
                self.profileActivated.emit(profile_id)
                self.statusMessage.emit(tr("status.activated", name=profile.label))
                self.refresh()
                return True
        return self.launch_profile(profile_id)

    def toggle_window(self, window_id: int) -> bool:
        window = next((w for w in self.windows if w.window_id == window_id), None)
        if window is None:
            return False
        if window.is_minimized:
            ok = self.backend.restore(window.window_id)
            self.statusMessage.emit(tr("status.window_restored"))
        else:
            ok = self.backend.minimize(window.window_id)
            self.statusMessage.emit(tr("status.window_minimized"))
        self.refresh()
        return ok

    def window_action(self, window_id: int, action: str) -> bool:
        """Runs an action on a window: activate, minimize, maximize or close."""
        window = next((w for w in self.windows if w.window_id == window_id), None)
        if window is None:
            return False
        if action == "activate":
            ok = self.backend.activate(window_id)
            self.statusMessage.emit(
                tr("status.window_activated") if ok else tr("status.window_activate_failed")
            )
        elif action == "minimize":
            ok = self.backend.minimize(window_id)
            self.statusMessage.emit(tr("status.window_minimized"))
        elif action == "restore":
            ok = self.backend.restore(window_id)
            self.statusMessage.emit(tr("status.window_restored"))
        elif action == "maximize":
            if window.is_maximized:
                ok = self.backend.unmaximize(window_id)
                self.statusMessage.emit(tr("status.window_unmaximized"))
            else:
                ok = self.backend.maximize(window_id)
                self.statusMessage.emit(tr("status.window_maximized"))
        elif action == "close":
            ok = self.backend.close_window(window_id)
            self.statusMessage.emit(
                tr("status.window_closed") if ok else tr("status.window_close_failed")
            )
        else:
            return False
        self.refresh()
        return ok

    def assign_window(self, window_id: int, profile_id: str) -> bool:
        window = next((w for w in self.windows if w.window_id == window_id), None)
        if window is None:
            return False
        self.database.assign_window(window_id, window.pid, profile_id, window.title, "manual")
        self._detached.pop((window_id, window.pid), None)
        window.profile_id = profile_id
        window.method = MatchMethod.MANUAL
        window.confidence = 1.0
        self.statusMessage.emit(tr("status.assigned"))
        self.refresh()
        return True

    def unassign_window(self, window_id: int) -> bool:
        """Forgets the profile of a window; it goes back to the unassigned card."""
        window = next((w for w in self.windows if w.window_id == window_id), None)
        if window is None:
            return False
        self.database.unassign_window(window_id, window.pid)
        self._detached[(window_id, window.pid)] = window.profile_id
        window.profile_id = None
        window.method = MatchMethod.NONE
        self.statusMessage.emit(tr("status.unassigned"))
        self.refresh()
        return True

    def adopt_active_window(self, profile_id: str) -> bool:
        window_id = self.backend.active_window()
        if window_id is None:
            self.statusMessage.emit(tr("status.adopt_failed"))
            return False
        window = next((w for w in self.windows if w.window_id == window_id), None)
        if window is None:
            self.statusMessage.emit(tr("status.adopt_not_brave"))
            return False
        return self.assign_window(window_id, profile_id)

    def open_profiles_manager(self) -> bool:
        if not self.launcher.available:
            self.statusMessage.emit(tr("status.brave_missing"))
            return False
        self.launcher.open_profile_manager()
        self.statusMessage.emit(tr("status.profiles_manager"))
        return True

    # -------------------------------------------------------- customisation

    def update_profile(self, profile_id: str, **fields) -> None:
        profile = self.profile(profile_id)
        if profile is None:
            return
        for key, value in fields.items():
            if hasattr(profile, key):
                setattr(profile, key, value)
        self.database.save_profile(profile)
        self.profilesChanged.emit()

    def rename_profile(self, profile_id: str, display_name: str) -> None:
        self.update_profile(profile_id, display_name=display_name.strip())

    def move_profile(self, profile_id: str, delta: int) -> None:
        ordered = sorted(self.profiles, key=lambda p: (p.sort_order, p.id))
        index = next((i for i, p in enumerate(ordered) if p.id == profile_id), None)
        if index is None:
            return
        target = index + delta
        if target < 0 or target >= len(ordered):
            return
        ordered[index], ordered[target] = ordered[target], ordered[index]
        for position, profile in enumerate(ordered):
            profile.sort_order = position
            self.database.save_profile(profile)
        self.profilesChanged.emit()

    def reorder_profiles(self, profile_ids: list[str]) -> None:
        """Applies the order the user gave by dragging the cards."""
        ordered = sorted(self.profiles, key=lambda p: (p.sort_order, p.id))
        by_id = {profile.id: profile for profile in ordered}
        nuevos = [by_id[pid] for pid in profile_ids if pid in by_id]
        nuevos += [profile for profile in ordered if profile.id not in profile_ids]
        for position, profile in enumerate(nuevos):
            profile.sort_order = position
            self.database.save_profile(profile)
        self.profiles = nuevos
        self.profilesChanged.emit()

    def reset_profile(self, profile_id: str) -> None:
        profile = self.profile(profile_id)
        if profile is None:
            return
        profile.display_name = ""
        profile.is_favorite = False
        profile.icon = "circle"
        profile.custom_image = ""
        profile.color = PROFILE_PALETTE[self.profiles.index(profile) % len(PROFILE_PALETTE)]
        self.database.save_profile(profile)
        self.profilesChanged.emit()

    # -------------------------------------------------------------- images

    def set_profile_image(self, profile_id: str, source: str | None) -> bool:
        """Copies a user chosen image into the app folder and links it."""
        profile = self.profile(profile_id)
        if profile is None:
            return False
        if source is None:
            self._borrar_imagen(profile)
            profile.custom_image = ""
            self.database.save_profile(profile)
            self.profilesChanged.emit()
            return True
        origen = Path(source).expanduser()
        if not origen.is_file():
            return False
        suffix = origen.suffix.lower()
        if suffix not in IMAGE_EXTENSIONS:
            return False
        destino = self._image_path(profile_id, suffix)
        try:
            destino.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(origen, destino)
        except OSError:
            return False
        self._borrar_imagen(profile)
        profile.custom_image = str(destino)
        self.database.save_profile(profile)
        self.profilesChanged.emit()
        return True

    def _borrar_imagen(self, profile: Profile) -> None:
        anterior = profile.custom_image
        if not anterior:
            return
        with contextlib.suppress(OSError):
            Path(anterior).unlink()

    def _image_path(self, profile_id: str, suffix: str) -> Path:
        safe = "".join(char for char in profile_id if char.isalnum() or char in "-_")
        return data_dir() / "images" / f"{safe or 'profile'}{suffix}"

    # -------------------------------------------------- profiles from windows

    def save_window_as_profile(self, window_id: int, name: str) -> str | None:
        """Creates a profile of the app that owns the given window."""
        window = next((w for w in self.windows if w.window_id == window_id), None)
        if window is None:
            return None
        profile_id = self._new_virtual_id()
        label = name.strip() or window.title.strip() or tr("profile.untitled")
        profile = Profile(
            id=profile_id,
            directory_name=profile_id,
            display_name=label,
            brave_display_name=label,
            color=PROFILE_PALETTE[len(self.profiles) % len(PROFILE_PALETTE)],
            icon="circle",
            sort_order=self.database.next_sort_order(),
            is_virtual=True,
            custom=True,
        )
        self.database.save_profile(profile)
        self.database.assign_window(window_id, window.pid, profile_id, window.title, "manual")
        self.statusMessage.emit(tr("status.profile_created"))
        self.refresh()
        return profile_id

    def _new_virtual_id(self) -> str:
        existing = {profile.id for profile in self.profiles}
        index = 1
        while f"virtual-{index}" in existing:
            index += 1
        return f"virtual-{index}"
