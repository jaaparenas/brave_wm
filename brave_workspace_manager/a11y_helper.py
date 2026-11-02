"""Lee las pestanas abiertas de las ventanas de Brave mediante AT-SPI.

Script autonomo: no importa el paquete, para poder ejecutarse con cualquier
interprete que tenga PyGObject disponible. Imprime un JSON con una entrada por
ventana de Brave:

    {"ok": true, "frames": [{"title": "...", "tabs": ["..."], "active": 0,
                              "geometry": [x, y, w, h]}]}

Si la libreria de accesibilidad no esta disponible responde
``{"ok": false, "reason": "..."}``.

Chromium solo publica el arbol de la interfaz (barra de pestanas incluida)
cuando el navegador se ha abierto con el modo de accesibilidad activado; si no,
las ventanas aparecen sin hijos y la lista de pestanas sale vacia.
"""

from __future__ import annotations

import json
import sys

ROLES_DE_CONTENIDO = ("document ", "page web")
PROFUNDIDAD_MAXIMA = 10


def _cargar_atspi():
    import gi

    gi.require_version("Atspi", "2.0")
    from gi.repository import Atspi

    return Atspi


def _hijos(nodo):
    try:
        total = nodo.get_child_count()
    except Exception:
        return
    for indice in range(total):
        try:
            hijo = nodo.get_child_at_index(indice)
        except Exception:
            continue
        if hijo is not None:
            yield hijo


def _rol(nodo) -> str:
    try:
        return nodo.get_role_name() or ""
    except Exception:
        return ""


def _nombre(nodo) -> str:
    try:
        return nodo.get_name() or ""
    except Exception:
        return ""


def _es_contenido_web(rol: str) -> bool:
    return any(rol.startswith(prefijo) for prefijo in ROLES_DE_CONTENIDO)


def _esta_mostrando(nodo, atspi) -> bool:
    try:
        return bool(nodo.get_state_set().contains(atspi.StateType.SHOWING))
    except Exception:
        return True


def _esta_seleccionada(nodo, atspi) -> bool:
    try:
        return bool(nodo.get_state_set().contains(atspi.StateType.SELECTED))
    except Exception:
        return False


def _listas_de_pestanas(nodo, atspi, profundidad: int = 0) -> list:
    """Localiza las franjas de pestanas (``page tab list``) dentro de un frame.

    Chromium deja dos franjas: la real, que esta mostrando, y una vacia y
    oculta. Se ignoran los subarboles de contenido web (la pagina cargada).
    """
    if profundidad > PROFUNDIDAD_MAXIMA:
        return []
    encontradas = []
    for hijo in _hijos(nodo):
        rol = _rol(hijo)
        if rol == "page tab list":
            encontradas.append(hijo)
            continue
        if _es_contenido_web(rol):
            continue
        encontradas.extend(_listas_de_pestanas(hijo, atspi, profundidad + 1))
    return encontradas


def _pestanas_de_la_lista(lista, atspi, profundidad: int = 0) -> list[tuple[str, bool]]:
    """Titulo y estado de seleccion de cada pestana de una franja."""
    pestanas: list[tuple[str, bool]] = []
    for hijo in _hijos(lista):
        if _rol(hijo) == "page tab":
            pestanas.append((_nombre(hijo), _esta_seleccionada(hijo, atspi)))
    if pestanas or profundidad >= 2:
        return pestanas
    for hijo in _hijos(lista):
        pestanas.extend(_pestanas_de_la_lista(hijo, atspi, profundidad + 1))
    return pestanas


def _mejor_franja(frame, atspi) -> list[tuple[str, bool]]:
    """La franja visible con mas pestanas; la lista de pestanas de la ventana."""
    candidatas = []
    for lista in _listas_de_pestanas(frame, atspi):
        pestanas = _pestanas_de_la_lista(lista, atspi)
        if not pestanas:
            continue
        candidatas.append((_esta_mostrando(lista, atspi), len(pestanas), pestanas))
    if not candidatas:
        return []
    candidatas.sort(key=lambda candidata: (candidata[0], candidata[1]), reverse=True)
    return candidatas[0][2]


def _geometria(frame, atspi) -> list[int] | None:
    try:
        ext = frame.get_extents(atspi.CoordType.SCREEN)
    except Exception:
        return None
    if ext is None or ext.width <= 0 or ext.height <= 0:
        return None
    return [int(ext.x), int(ext.y), int(ext.width), int(ext.height)]


def _frames_de_brave(atspi) -> list[dict]:
    escritorio = atspi.get_desktop(0)
    frames: list[dict] = []
    for aplicacion in _hijos(escritorio):
        if "brave" not in _nombre(aplicacion).lower():
            continue
        for frame in _hijos(aplicacion):
            if _rol(frame) not in ("frame", "window"):
                continue
            pestanas = _mejor_franja(frame, atspi)
            activa = -1
            for indice, (_, seleccionada) in enumerate(pestanas):
                if seleccionada:
                    activa = indice
                    break
            frames.append(
                {
                    "title": _nombre(frame),
                    "tabs": [titulo for titulo, _ in pestanas],
                    "active": activa,
                    "geometry": _geometria(frame, atspi),
                }
            )
    return frames


def main() -> int:
    try:
        atspi = _cargar_atspi()
    except Exception as exc:
        print(json.dumps({"ok": False, "reason": f"atspi-no-disponible: {exc}"}))
        return 0
    try:
        frames = _frames_de_brave(atspi)
    except Exception as exc:
        print(json.dumps({"ok": False, "reason": f"error-leyendo: {exc}"}))
        return 0
    print(json.dumps({"ok": True, "frames": frames}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
