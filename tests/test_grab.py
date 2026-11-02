"""Pruebas de la captura de atajos globales."""

from __future__ import annotations

import pytest
from Xlib import X

from brave_workspace_manager.x11.grab import ShortcutGrabber, parse_sequence


def test_parse_sequence_splits_modifiers_and_key() -> None:
    modifiers, key = parse_sequence("Ctrl+Alt+1")
    assert modifiers == {"ctrl", "alt"}
    assert key == "1"


def test_parse_sequence_accepts_a_single_key() -> None:
    assert parse_sequence("F5") == (set(), "f5")


def test_parse_sequence_rejects_an_empty_sequence() -> None:
    with pytest.raises(ValueError):
        parse_sequence("  ")


def _grabber_with(bindings: dict[tuple[int, int], str]) -> ShortcutGrabber:
    grabber = ShortcutGrabber(lambda action: None)
    grabber._bindings = dict(bindings)
    return grabber


def test_match_requires_the_bound_keycode() -> None:
    grabber = _grabber_with({(18, X.ControlMask | X.Mod1Mask): "profile-9"})
    assert grabber._match(18, X.ControlMask | X.Mod1Mask) == "profile-9"
    assert grabber._match(19, X.ControlMask | X.Mod1Mask) is None


def test_match_requires_every_modifier() -> None:
    grabber = _grabber_with({(18, X.ControlMask | X.Mod1Mask): "profile-9"})
    assert grabber._match(18, X.ControlMask) is None
    assert grabber._match(18, X.ControlMask | X.Mod1Mask) == "profile-9"


def test_match_prefers_the_most_specific_binding() -> None:
    grabber = _grabber_with(
        {
            (23, X.ControlMask | X.Mod1Mask): "next-profile",
            (23, X.ControlMask | X.Mod1Mask | X.ShiftMask): "prev-profile",
        }
    )
    state = X.ControlMask | X.Mod1Mask | X.ShiftMask
    assert grabber._match(23, state) == "prev-profile"
    assert grabber._match(23, X.ControlMask | X.Mod1Mask) == "next-profile"
