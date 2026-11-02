"""Wakes up Brave's accessibility tree without restarting the browser.

Chromium builds the accessibility tree of its interface (tab strip included)
only when an assistive technology is present. Besides the start-up flag
``--force-renderer-accessibility``, it watches the ``ScreenReaderEnabled``
property of the AT-SPI bus (``org.a11y.Bus``) and enables accessibility at run
time when it turns true, keeping it enabled afterwards.

The switch turns that property on for a few seconds and then restores its
previous value. It does not touch GNOME settings and does not start a screen
reader.
"""

from __future__ import annotations

import shutil
import subprocess

BUS_ARGS = ("--user", "org.a11y.Bus", "/org/a11y/bus", "org.a11y.Status", "ScreenReaderEnabled")


class A11ySwitch:
    """Reads and writes ``org.a11y.Status.ScreenReaderEnabled`` through busctl."""

    def __init__(self, binary: str | None = None) -> None:
        self._binary = binary if binary is not None else shutil.which("busctl")

    @property
    def available(self) -> bool:
        return bool(self._binary)

    def _run(self, *args: str) -> subprocess.CompletedProcess | None:
        if not self._binary:
            return None
        try:
            return subprocess.run(
                [self._binary, *args], capture_output=True, text=True, timeout=5, check=False
            )
        except (OSError, subprocess.SubprocessError):
            return None

    def get(self) -> bool | None:
        """Current value, or None when the bus cannot be queried."""
        user, *rest = BUS_ARGS
        result = self._run(user, "get-property", *rest)
        if result is None or result.returncode != 0:
            return None
        return result.stdout.strip().endswith("true")

    def set(self, enabled: bool) -> bool:
        user, *rest = BUS_ARGS
        result = self._run(user, "set-property", *rest, "b", "true" if enabled else "false")
        return result is not None and result.returncode == 0
