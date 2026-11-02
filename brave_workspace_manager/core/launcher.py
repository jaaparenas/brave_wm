"""Apertura de perfiles nativos de Brave sin crear instancias conflictivas."""

from __future__ import annotations

import subprocess
from pathlib import Path

PROFILE_MANAGER_URL = "brave://settings/manageProfile"


class ProfileLauncher:
    """Invoca el ejecutable de Brave con el directorio de perfil nativo."""

    def __init__(self, binary: str | None, user_data_dir: Path) -> None:
        self.binary = binary
        self.user_data_dir = Path(user_data_dir)

    @property
    def available(self) -> bool:
        return bool(self.binary)

    def _spawn(self, args: list[str]) -> bool:
        if not self.binary:
            return False
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
        """Abre (o trae al frente) el perfil indicado usando su directorio nativo."""
        return self._spawn([f"--profile-directory={directory_name}"])

    def open_profile_manager(self) -> bool:
        """Abre el gestor de perfiles de Brave; no se escriben bases de datos ajenas."""
        return self._spawn([PROFILE_MANAGER_URL])

    def open_url(self, url: str) -> bool:
        return self._spawn([url])
