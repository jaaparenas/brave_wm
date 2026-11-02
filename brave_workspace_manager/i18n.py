"""Translations: one JSON file per language, inside ``locales/``.

Adding a language is a matter of dropping a new ``<code>.json`` file next to
the existing ones; the interface picks it up without any code change.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

LOCALES_DIR = Path(__file__).resolve().parent / "locales"
FALLBACK_LANGUAGE = "en"
NAME_KEY = "language_name"


def detect_system_language() -> str:
    """Language code of the running system (``es``, ``en``, ...)."""
    for variable in ("LC_ALL", "LC_MESSAGES", "LANG", "LANGUAGE"):
        value = os.environ.get(variable)
        if not value:
            continue
        code = value.split(":")[0].split(".")[0].split("_")[0].strip().lower()
        if code:
            return code
    return FALLBACK_LANGUAGE


class Translator:
    """Loads the catalogues and translates keys."""

    def __init__(self, language: str | None = None, directory: Path | None = None) -> None:
        self.directory = Path(directory) if directory else LOCALES_DIR
        self._catalogues: dict[str, dict[str, str]] = {}
        self._language = FALLBACK_LANGUAGE
        self.set_language(language or FALLBACK_LANGUAGE)

    # ------------------------------------------------------------- catalogues

    def available_languages(self) -> list[str]:
        """Language codes with a catalogue file, always including the fallback."""
        codes = sorted(path.stem for path in self.directory.glob("*.json"))
        return codes or [FALLBACK_LANGUAGE]

    def _catalogue(self, code: str) -> dict[str, str]:
        if code not in self._catalogues:
            path = self.directory / f"{code}.json"
            data: dict[str, str] = {}
            try:
                raw = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                raw = {}
            if isinstance(raw, dict):
                data = {str(key): str(value) for key, value in raw.items()}
            self._catalogues[code] = data
        return self._catalogues[code]

    # ---------------------------------------------------------------- language

    @property
    def language(self) -> str:
        return self._language

    def set_language(self, code: str | None) -> str:
        """Selects a language; unknown codes fall back to the closest match."""
        code = (code or "").strip().lower()
        available = self.available_languages()
        if code not in available:
            base = code.split("_")[0]
            code = base if base in available else FALLBACK_LANGUAGE
        self._language = code
        return code

    def language_name(self, code: str) -> str:
        """Name of a language, written in that same language."""
        name = self._catalogue(code).get(NAME_KEY, "")
        return name or code.upper()

    # -------------------------------------------------------------- translating

    def tr(self, key: str, **values) -> str:
        """Text of a key in the active language, or the key itself."""
        text = self._catalogue(self._language).get(key)
        if text is None:
            text = self._catalogue(FALLBACK_LANGUAGE).get(key)
        if text is None:
            return key
        if not values:
            return text
        try:
            return text.format(**values)
        except (KeyError, IndexError, ValueError):
            return text


_translator = Translator()


def tr(key: str, **values) -> str:
    """Text of a key in the active language."""
    return _translator.tr(key, **values)


def set_language(code: str | None) -> str:
    """Changes the active language and returns the code really in use."""
    return _translator.set_language(code)


def current_language() -> str:
    return _translator.language


def available_languages() -> list[str]:
    return _translator.available_languages()


def language_name(code: str) -> str:
    return _translator.language_name(code)
