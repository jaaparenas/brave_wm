"""Opens native Brave profiles without creating conflicting instances."""

from __future__ import annotations

import subprocess
from pathlib import Path

PROFILE_MANAGER_URL = "brave://settings/manageProfile"

# Chromium only publishes its interface (tab strip included) through AT-SPI
# when the browser is started with accessibility mode enabled.
FLAG_ACCESIBILIDAD = "--force-renderer-accessibility"


class ProfileLauncher:
    """Runs the Brave executable with the native profile directory."""

    def __init__(self, binary: str | None, user_data_dir: Path, leer_pestanas: bool = True) -> None:
        self.binary = binary
        self.user_data_dir = Path(user_data_dir)
        self.leer_pestanas = leer_pestanas

    @property
    def available(self) -> bool:
        return bool(self.binary)

    def _spawn(self, args: list[str]) -> bool:
        if not self.binary:
            return False
        if self.leer_pestanas:
            args = [*args, FLAG_ACCESIBILIDAD]
        try:
            subprocess.Popen(
                [self.binary, *args],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                stdin=subprocess.DEVNULL,
                start_new_session=True,
            )
        except (OSError, ValueError):
            return False
        return True

    def launch(self, directory_name: str) -> bool:
        """Opens (or raises) the given profile using its native directory."""
        return self._spawn([f"--profile-directory={directory_name}"])

    def open_profile_manager(self) -> bool:
        """Opens Brave's profile manager; no foreign database is ever written."""
        return self._spawn([PROFILE_MANAGER_URL])

    def open_url(self, url: str) -> bool:
        return self._spawn([url])
