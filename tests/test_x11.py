"""Tests of the decoding of X11 properties."""

from __future__ import annotations

from array import array

from brave_workspace_manager.x11.backend import X11Backend


def test_decodes_bytes() -> None:
    assert X11Backend._as_text(b"Brave") == "Brave"


def test_decodes_tuple_of_strings() -> None:
    assert X11Backend._as_text(("brave-browser", "Brave-browser")) == (
        "brave-browser\x00Brave-browser"
    )


def test_decodes_list_of_bytes() -> None:
    assert X11Backend._as_text([b"uno", b"dos"]) == "uno\x00dos"


class _FakeProperty:
    def __init__(self, value):
        self.value = value


class _FakeBackend(X11Backend):
    def __init__(self, value):
        self._value = value

    def _property(self, window, name):
        return _FakeProperty(self._value)


def test_int_property_reads_cardinal_arrays() -> None:
    backend = _FakeBackend(array("I", [56950]))
    assert backend._int_property(None, "_NET_WM_PID") == 56950


def test_int_property_reads_plain_integers() -> None:
    assert _FakeBackend(42)._int_property(None, "x") == 42


def test_int_property_handles_missing_values() -> None:
    assert _FakeBackend(None)._int_property(None, "x") == 0
    assert _FakeBackend(array("I", []))._int_property(None, "x") == 0


def test_int_property_handles_unsupported_values() -> None:
    assert _FakeBackend("texto")._int_property(None, "x") == 0
