"""Controlador: coordina descubrimiento de perfiles, ventanas y acciones."""

from __future__ import annotations

import os
import time
from pathlib import Path

from PySide6.QtCore import QObject, QThread, QTimer, Signal

from .. import discovery, processes
from ..config import brave_user_data_dir
from ..database import Database
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


class TabReaderThread(QThread):
    """Lee las pestanas de Brave fuera del hilo de la interfaz."""

    tabsRead = Signal(list)

    def __init__(self, reader: TabReader) -> None:
        super().__init__()
        self._reader = reader

    def run(self) -> None:  # pragma: no cover - depende del entorno
        try:
            frames = self._reader.read()
        except Exception:
            frames = []
        self.tabsRead.emit(frames)


class AppController(QObject):
    """Estado compartido de la aplicacion."""

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
        self._frames: list[FrameTabs] = []
        self._tab_thread: TabReaderThread | None = None
        self._last_tab_read = 0.0
        self._leer_pestanas = True
        self._sin_accesibilidad: set[int] = set()
        self._navegador_abierto = False

    # ------------------------------------------------------------ ciclo de vida

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

    def set_poll_interval(self, milliseconds: int) -> None:
        self.poll_interval_ms = max(500, int(milliseconds))
        if self._timer is not None:
            self._timer.setInterval(self.poll_interval_ms)

    # --------------------------------------------------------------- estado

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
        """Aviso sobre la lectura de pestanas; vacio si funciona."""
        if not self._leer_pestanas:
            return ""
        motivo = self.tab_reader.motivo
        if motivo:
            return f"No se puede leer el número de pestañas: {motivo}"
        if self._sin_accesibilidad:
            return (
                "Brave está en marcha sin el modo de accesibilidad, así que solo se ve "
                "la pestaña activa de cada ventana. Cierra Brave del todo y vuelve a "
                "abrir un perfil desde la aplicación para listar todas las pestañas."
            )
        return ""

    def set_read_tabs(self, enabled: bool) -> None:
        """Activa o desactiva la lectura de pestañas y el flag del lanzador."""
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

    # ------------------------------------------------------------ actualizacion

    def refresh(self) -> None:
        found = discovery.discover_profiles(self.user_data_dir)
        self.profiles = self._merge_profiles(found)

        process_list = processes.scan_brave_processes()
        browser_pids = [p.pid for p in processes.browser_processes(process_list)]
        self._navegador_abierto = bool(browser_pids)
        accesibilidad = processes.accesibilidad_por_pid(process_list)
        known_dirs = {p.directory_name for p in self.profiles}
        open_dirs = processes.profile_dirs_in_use(browser_pids, self.user_data_dir, known_dirs)

        windows = self._brave_windows(process_list)
        self._sin_accesibilidad = {
            w.window_id for w in windows if w.pid in accesibilidad and not accesibilidad[w.pid]
        }
        self._learn_from_launch(windows)

        assignments = self.database.load_assignments()
        context = ResolutionContext(
            profiles=self.profiles,
            windows=windows,
            open_profile_ids=open_dirs,
            assignments=assignments,
        )
        self.resolver.resolve(context)

        for profile in self.profiles:
            profile.is_open = profile.id in open_dirs
            profile.window_count = sum(1 for w in windows if w.profile_id == profile.id)

        self.windows = windows
        self._aplicar_pestanas(windows, self._frames)
        self._programar_lectura_pestanas()
        self.profilesChanged.emit()
        self.windowsChanged.emit()

    # -------------------------------------------------------------- pestanas

    def _aplicar_pestanas(self, windows: list[WindowInfo], frames: list[FrameTabs]) -> None:
        """Reparte las pestanas leidas entre las ventanas y los perfiles."""
        pares = emparejar(frames, windows) if frames else {}
        for window in windows:
            frame = pares.get(window.window_id)
            window.tab_count = frame.count if frame else 0
            window.tab_titles = list(frame.titles) if frame else []
            window.active_tab = frame.active if frame else -1
        for profile in self.profiles:
            profile.tab_count = sum(w.tab_count for w in windows if w.profile_id == profile.id)

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
        self.profilesChanged.emit()
        self.windowsChanged.emit()

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

    # --------------------------------------------------------------- acciones

    def launch_profile(self, profile_id: str) -> bool:
        profile = self.profile(profile_id)
        if profile is None:
            return False
        if not self.launcher.available:
            self.statusMessage.emit("No se encuentra el ejecutable de Brave.")
            return False
        self._baseline_window_ids = {w.window_id for w in self.windows}
        self._launch_target = profile_id
        self._launch_deadline = time.monotonic() + LAUNCH_LEARNING_SECONDS
        if self.launcher.launch(profile.directory_name):
            self.statusMessage.emit(f"Abriendo {profile.label}...")
            return True
        self._launch_target = None
        self.statusMessage.emit("No se pudo abrir Brave.")
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
                self.database.assign_window(
                    target.window_id, target.pid, profile_id, target.title, "learned"
                )
                self.profileActivated.emit(profile_id)
                self.statusMessage.emit(f"{profile.label} activada.")
                self.refresh()
                return True
        return self.launch_profile(profile_id)

    def toggle_window(self, window_id: int) -> bool:
        window = next((w for w in self.windows if w.window_id == window_id), None)
        if window is None:
            return False
        if window.is_minimized:
            ok = self.backend.restore(window.window_id)
            self.statusMessage.emit("Ventana restaurada.")
        else:
            ok = self.backend.minimize(window.window_id)
            self.statusMessage.emit("Ventana minimizada.")
        self.refresh()
        return ok

    def assign_window(self, window_id: int, profile_id: str) -> bool:
        window = next((w for w in self.windows if w.window_id == window_id), None)
        if window is None:
            return False
        self.database.assign_window(window_id, window.pid, profile_id, window.title, "manual")
        window.profile_id = profile_id
        window.method = MatchMethod.MANUAL
        window.confidence = 1.0
        self.statusMessage.emit("Ventana asignada al perfil.")
        self.refresh()
        return True

    def adopt_active_window(self, profile_id: str) -> bool:
        window_id = self.backend.active_window()
        if window_id is None:
            self.statusMessage.emit("No se pudo detectar la ventana activa.")
            return False
        window = next((w for w in self.windows if w.window_id == window_id), None)
        if window is None:
            self.statusMessage.emit("La ventana activa no pertenece a Brave.")
            return False
        return self.assign_window(window.window_id, profile_id)

    def open_profiles_manager(self) -> bool:
        if not self.launcher.available:
            self.statusMessage.emit("No se encuentra el ejecutable de Brave.")
            return False
        self.launcher.open_profile_manager()
        self.statusMessage.emit("Abriendo el gestor de perfiles de Brave.")
        return True

    # ------------------------------------------------------- personalizacion

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

    def reset_profile(self, profile_id: str) -> None:
        profile = self.profile(profile_id)
        if profile is None:
            return
        profile.display_name = ""
        profile.is_favorite = False
        profile.icon = "circle"
        profile.color = PROFILE_PALETTE[self.profiles.index(profile) % len(PROFILE_PALETTE)]
        self.database.save_profile(profile)
        self.profilesChanged.emit()
