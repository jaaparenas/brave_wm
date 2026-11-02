"""Reading of the tabs of every Brave window and matching with the windows.

Chromium does not expose its tabs through X11/EWMH: only the window title (the
active tab). The local way is the accessibility tree (AT-SPI), which is read in
a separate process because the virtual environment of the application may not
have PyGObject.

The browser only publishes its interface (and with it the tab strip) when it
was started with accessibility mode enabled; that is why the launcher adds
``--force-renderer-accessibility`` to the profiles it opens.
"""

from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

from .models import WindowInfo

HELPER_NAME = "a11y_helper.py"
TIMEOUT_SEGUNDOS = 6.0
REINTENTO_SEGUNDOS = 300.0
UMBRAL_SOLAPE = 0.4
# When several profiles exist, Brave appends an en dash and the profile name to the
# accessible name of every window, right after the "- Brave" application suffix.
PROFILE_SEPARATOR = " \u2013 "
APP_SUFFIX = "Brave"


@dataclass(slots=True)
class FrameTabs:
    """Tabs of a Brave window according to the accessibility tree."""

    title: str = ""
    titles: list[str] = field(default_factory=list)
    active: int = -1
    geometry: tuple[int, int, int, int] | None = None

    @property
    def count(self) -> int:
        return len(self.titles)

    @property
    def profile_name(self) -> str:
        """Name of the Brave profile that owns the window, when Brave shows it."""
        head, separator, tail = self.title.rpartition(PROFILE_SEPARATOR)
        if not separator or not head.rstrip().endswith(APP_SUFFIX):
            return ""
        return tail.strip()

    @property
    def window_title(self) -> str:
        """The title as X11 sees it, without the profile name."""
        if self.profile_name:
            return self.title.rpartition(PROFILE_SEPARATOR)[0]
        return self.title

    @property
    def active_title(self) -> str:
        """Title of the foreground tab, when known."""
        if 0 <= self.active < len(self.titles):
            return self.titles[self.active]
        return ""


class SinLecturaTabs:
    """Stand-in reader that queries nothing (screenshots and tests)."""

    motivo = ""
    disponible = False

    def read(self) -> list[FrameTabs]:
        return []


def normalizar(titulo: str) -> str:
    return " ".join(titulo.split()).casefold()


def solape(primero: tuple[int, int, int, int], segundo: tuple[int, int, int, int]) -> float:
    """Overlap ratio between two rectangles."""
    ax, ay, aw, ah = primero
    bx, by, bw, bh = segundo
    ancho = max(0, min(ax + aw, bx + bw) - max(ax, bx))
    alto = max(0, min(ay + ah, by + bh) - max(ay, by))
    interseccion = ancho * alto
    if interseccion == 0:
        return 0.0
    union = aw * ah + bw * bh - interseccion
    return interseccion / union if union > 0 else 0.0


class TabReader:
    """Runs the accessibility helper and returns the tabs it read."""

    def __init__(
        self,
        helper_path: Path | None = None,
        timeout: float = TIMEOUT_SEGUNDOS,
    ) -> None:
        self._helper = Path(helper_path) if helper_path else Path(__file__).with_name(HELPER_NAME)
        self._timeout = timeout
        self._interprete: str | None = None
        self._fallo_en: float = 0.0
        self.motivo: str = ""

    @property
    def disponible(self) -> bool:
        return self._helper.exists()

    def read(self) -> list[FrameTabs]:
        """Tabs of every Brave window; an empty list when they cannot be read."""
        if not self.disponible:
            self.motivo = "The accessibility helper is missing."
            return []
        if self._interprete is None:
            return self._buscar_interprete()
        datos = self._ejecutar(self._interprete)
        if datos is None:
            self._interprete = None
            return self._buscar_interprete()
        if not datos.get("ok"):
            self.motivo = str(datos.get("reason", "Sin soporte de accesibilidad."))
            return []
        self.motivo = ""
        return self._parsear(datos)

    def _buscar_interprete(self) -> list[FrameTabs]:
        for interprete in self._interpretes():
            datos = self._ejecutar(interprete)
            if datos is None:
                continue
            if not datos.get("ok"):
                self.motivo = str(datos.get("reason", "Sin soporte de accesibilidad."))
                continue
            self._interprete = interprete
            self.motivo = ""
            return self._parsear(datos)
        return []

    def _interpretes(self) -> list[str]:
        candidatos = [sys.executable, "/usr/bin/python3"]
        unicos: list[str] = []
        for candidato in candidatos:
            if candidato and candidato not in unicos:
                unicos.append(candidato)
        return unicos

    def _ejecutar(self, interprete: str) -> dict | None:
        try:
            proceso = subprocess.run(
                [interprete, str(self._helper)],
                capture_output=True,
                text=True,
                timeout=self._timeout,
                check=False,
            )
        except (OSError, subprocess.SubprocessError):
            return None
        if proceso.returncode != 0:
            return None
        try:
            datos = json.loads(proceso.stdout or "{}")
        except json.JSONDecodeError:
            return None
        return datos if isinstance(datos, dict) else None

    @staticmethod
    def _parsear(datos: dict) -> list[FrameTabs]:
        frames: list[FrameTabs] = []
        for item in datos.get("frames", []):
            if not isinstance(item, dict):
                continue
            titulos = [str(titulo) for titulo in item.get("tabs", [])]
            geometria = item.get("geometry")
            rect: tuple[int, int, int, int] | None = None
            if isinstance(geometria, (list, tuple)) and len(geometria) == 4:
                try:
                    rect = tuple(int(valor) for valor in geometria)  # type: ignore[assignment]
                except (TypeError, ValueError):
                    rect = None
            try:
                activa = int(item.get("active", -1))
            except (TypeError, ValueError):
                activa = -1
            frames.append(
                FrameTabs(
                    title=str(item.get("title", "")),
                    titles=titulos,
                    active=activa,
                    geometry=rect,
                )
            )
        return frames


def emparejar(frames: list[FrameTabs], windows: list[WindowInfo]) -> dict[int, FrameTabs]:
    """Links every X11 window with its tabs, when it can be determined."""
    resultado: dict[int, FrameTabs] = {}
    emparejados = {id(frame) for frame in resultado.values()}
    disponibles = list(windows)

    for frame in frames:
        clave = normalizar(frame.window_title)
        if not clave:
            continue
        candidatos = [w for w in disponibles if normalizar(w.title) == clave]
        if len(candidatos) == 1:
            ventana = candidatos[0]
            resultado[ventana.window_id] = frame
            emparejados.add(id(frame))
            disponibles.remove(ventana)

    # Brave may insert notices before the suffix ("- High memory usage - 885 MB"),
    # so the start of the title is compared too.
    for frame in frames:
        if id(frame) in emparejados:
            continue
        clave = normalizar(frame.window_title)
        candidatos = [
            w for w in disponibles if (base := _sin_sufijo(w.title)) and clave.startswith(base)
        ]
        if len(candidatos) == 1:
            resultado[candidatos[0].window_id] = frame
            emparejados.add(id(frame))
            disponibles.remove(candidatos[0])

    for frame in frames:
        if id(frame) in emparejados or frame.geometry is None:
            continue
        mejor = None
        mejor_valor = UMBRAL_SOLAPE
        for ventana in disponibles:
            if ventana.width <= 0 or ventana.height <= 0:
                continue
            valor = solape(frame.geometry, (ventana.x, ventana.y, ventana.width, ventana.height))
            if valor > mejor_valor:
                mejor_valor = valor
                mejor = ventana
        if mejor is not None:
            resultado[mejor.window_id] = frame
            emparejados.add(id(frame))
            disponibles.remove(mejor)

    if len(disponibles) == 1:
        pendientes = [frame for frame in frames if id(frame) not in emparejados]
        if len(pendientes) == 1 and _coinciden(pendientes[0], disponibles[0]):
            resultado[disponibles[0].window_id] = pendientes[0]

    return resultado


def _sin_sufijo(titulo: str) -> str:
    """Normalised X11 title without the trailing "- Brave"."""
    clave = normalizar(titulo)
    suffix = " - " + APP_SUFFIX.casefold()
    if clave.endswith(suffix):
        clave = clave[: -len(suffix)]
    return clave if len(clave) >= 3 else ""


def _coinciden(frame: FrameTabs, ventana: WindowInfo) -> bool:
    """Without geometry there is no contradiction; with it they must overlap."""
    if frame.geometry is None or ventana.width <= 0 or ventana.height <= 0:
        return True
    rect = (ventana.x, ventana.y, ventana.width, ventana.height)
    return solape(frame.geometry, rect) >= UMBRAL_SOLAPE
