"""Inspeccion de los procesos de Brave mediante /proc."""

from __future__ import annotations

import os
import re
from collections.abc import Iterable
from pathlib import Path

from .models import BrowserProcess

BROWSER_TYPE = "browser"


def _read_cmdline(pid: int) -> list[str]:
    try:
        with open(f"/proc/{pid}/cmdline", "rb") as handle:
            raw = handle.read()
    except OSError:
        return []
    if not raw:
        return []
    return [part.decode("utf-8", "replace") for part in raw.split(b"\0") if part]


def _exe_name(pid: int) -> str:
    try:
        return os.path.basename(os.readlink(f"/proc/{pid}/exe"))
    except OSError:
        return ""


def _looks_like_brave(pid: int, cmdline: list[str]) -> bool:
    if "brave" in _exe_name(pid).lower():
        return True
    for argument in cmdline[:2]:
        base = os.path.basename(argument).lower()
        if base.startswith("brave-browser") or base == "brave":
            return True
    return False


def _flag(cmdline: list[str], name: str) -> str | None:
    """Extrae un flag de la linea de comandos.

    Chromium reescribe el titulo de sus procesos secundarios, de modo que
    /proc/<pid>/cmdline llega como una unica cadena con espacios en lugar de
    argumentos separados; por eso se busca primero en los argumentos sueltos y
    despues, como ultimo recurso, sobre el texto completo.
    """
    for index, argument in enumerate(cmdline):
        if argument.startswith(f"--{name}="):
            return argument.split("=", 1)[1].strip("\"'")
        if argument == f"--{name}" and index + 1 < len(cmdline):
            return cmdline[index + 1]
    text = " ".join(cmdline)
    match = re.search(rf"--{re.escape(name)}=(.+?)(?:\s+--|$)", text)
    if match:
        return match.group(1).strip("\"'")
    match = re.search(rf"--{re.escape(name)}\s+(\S+)", text)
    if match:
        return match.group(1)
    return None


def _process_kind(cmdline: list[str]) -> str:
    kind = _flag(cmdline, "type")
    return kind or BROWSER_TYPE


def scan_brave_processes() -> list[BrowserProcess]:
    """Procesos de Brave vivos; los que desaparecen durante el recorrido se ignoran."""
    processes: list[BrowserProcess] = []
    try:
        pids = [int(entry) for entry in os.listdir("/proc") if entry.isdigit()]
    except OSError:
        return processes
    for pid in pids:
        cmdline = _read_cmdline(pid)
        if not cmdline or not _looks_like_brave(pid, cmdline):
            continue
        try:
            ppid = int(_read_status_field(pid, "PPid"))
        except (OSError, ValueError):
            ppid = 0
        processes.append(
            BrowserProcess(
                pid=pid,
                ppid=ppid,
                kind=_process_kind(cmdline),
                cmdline=cmdline,
                profile_directory=_flag(cmdline, "profile-directory"),
                user_data_dir=_flag(cmdline, "user-data-dir"),
            )
        )
    return processes


def _read_status_field(pid: int, field: str) -> str:
    try:
        with open(f"/proc/{pid}/status", encoding="utf-8") as handle:
            for line in handle:
                if line.startswith(field + ":"):
                    return line.split(":", 1)[1].strip()
    except OSError:
        pass
    return "0"


def browser_processes(processes: Iterable[BrowserProcess]) -> list[BrowserProcess]:
    return [process for process in processes if process.kind == BROWSER_TYPE]


def accesibilidad_activada(processes: Iterable[BrowserProcess]) -> bool:
    """True si algun proceso del navegador se abrio con el modo de accesibilidad."""
    return any(accesibilidad_por_pid(processes).values())


def accesibilidad_por_pid(processes: Iterable[BrowserProcess]) -> dict[int, bool]:
    """Que proceso del navegador se abrio con el modo de accesibilidad.

    Chromium solo publica su interfaz por AT-SPI cuando se arranca con
    ``--force-renderer-accessibility``; si el navegador ya estaba en marcha, el
    proceso no lo lleva y sus ventanas no muestran mas que la pestana activa.
    """
    resultado: dict[int, bool] = {}
    for proceso in processes:
        if proceso.kind != BROWSER_TYPE:
            continue
        resultado[proceso.pid] = _flag_accesibilidad(proceso.cmdline)
    return resultado


def _flag_accesibilidad(cmdline: list[str]) -> bool:
    flag = "--force-renderer-accessibility"
    for argumento in cmdline:
        if argumento == flag or argumento.startswith(f"{flag}="):
            return True
    return flag in " ".join(cmdline)


def match_profile_directory(
    target: str, user_data_dir: Path, known_profiles: set[str]
) -> str | None:
    """Nombre del perfil al que pertenece una ruta, si es un perfil conocido."""
    prefix = str(Path(user_data_dir)) + os.sep
    if not target.startswith(prefix):
        return None
    head = target[len(prefix) :].split(os.sep, 1)[0]
    return head if head in known_profiles else None


def profile_dirs_in_use(
    pids: Iterable[int], user_data_dir: Path, known_profiles: set[str]
) -> set[str]:
    """Perfiles que el proceso de Brave tiene abiertos (ficheros abiertos en la carpeta).

    Chromium mantiene el perfil cargado en el proceso raiz, de modo que los
    descriptores abiertos al directorio del perfil revelan que perfiles estan
    activos, sin depender de titulos de ventana.
    """
    found: set[str] = set()
    for pid in pids:
        fd_dir = f"/proc/{pid}/fd"
        try:
            entries = os.listdir(fd_dir)
        except OSError:
            continue
        for entry in entries:
            try:
                target = os.readlink(f"{fd_dir}/{entry}")
            except OSError:
                continue
            name = match_profile_directory(target, user_data_dir, known_profiles)
            if name:
                found.add(name)
    return found


def window_pids(processes: Iterable[BrowserProcess]) -> set[int]:
    """PIDs que pueden ser proprietarios de ventanas de Brave."""
    return {process.pid for process in processes}
