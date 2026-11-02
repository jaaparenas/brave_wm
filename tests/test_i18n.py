"""Tests of the translation layer and of the language catalogues."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from brave_workspace_manager import i18n

LOCALES_DIR = Path(i18n.LOCALES_DIR)


@pytest.fixture(autouse=True)
def restore_language():
    """Every test starts and ends with the language it found."""
    previous = i18n.current_language()
    yield
    i18n.set_language(previous)


def test_every_catalogue_has_the_same_keys() -> None:
    catalogues = {}
    for path in sorted(LOCALES_DIR.glob("*.json")):
        catalogues[path.stem] = json.loads(path.read_text(encoding="utf-8"))
    assert len(catalogues) >= 2
    reference = set(catalogues["en"])
    for code, catalogue in catalogues.items():
        assert set(catalogue) == reference, f"{code} does not match en"
        assert all(value.strip() for value in catalogue.values()), f"{code} has empty texts"


def test_available_languages_are_listed() -> None:
    languages = i18n.available_languages()
    assert "en" in languages
    assert "es" in languages
    assert languages == sorted(languages)


def test_language_is_shown_in_its_own_language() -> None:
    assert i18n.language_name("en") == "English"
    assert i18n.language_name("es") == "Español"


def test_translation_follows_the_selected_language() -> None:
    i18n.set_language("en")
    english = i18n.tr("header.refresh")
    i18n.set_language("es")
    spanish = i18n.tr("header.refresh")
    assert english != spanish
    assert i18n.current_language() == "es"


def test_unknown_language_falls_back_to_english() -> None:
    i18n.set_language("xx")
    assert i18n.current_language() == "en"


def test_unknown_key_returns_the_key_itself() -> None:
    assert i18n.tr("does.not.exist") == "does.not.exist"


def test_placeholders_are_replaced() -> None:
    i18n.set_language("en")
    text = i18n.tr("card.tabs.many", count=7)
    assert "7" in text


def test_english_is_the_fallback_of_the_spanish_catalogue() -> None:
    """A key missing in Spanish falls back to the English text."""
    spanish = json.loads((LOCALES_DIR / "es.json").read_text(encoding="utf-8"))
    english = json.loads((LOCALES_DIR / "en.json").read_text(encoding="utf-8"))
    missing = set(english) - set(spanish)
    assert not missing, f"Spanish is missing: {sorted(missing)}"
