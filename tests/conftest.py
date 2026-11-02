"""Fixtures compartidas por la bateria de pruebas."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from brave_workspace_manager.models import Profile, WindowInfo


@pytest.fixture
def fake_brave_root(tmp_path: Path) -> Path:
    """Directorio de datos de Brave simulado con dos perfiles."""
    root = tmp_path / "Brave-Browser"
    root.mkdir()
    local_state = {
        "profile": {
            "last_used": "Default",
            "last_active_profiles": ["Default", "Profile 1"],
            "info_cache": {
                "Default": {
                    "name": "Alice Doe",
                    "gaia_name": "",
                    "active_time": 1700000000.0,
                },
                "Profile 1": {
                    "name": "Work",
                    "gaia_name": "sync account",
                    "active_time": 1700000100.0,
                },
            },
        }
    }
    (root / "Local State").write_text(json.dumps(local_state), encoding="utf-8")
    for name in ("Default", "Profile 1"):
        profile_dir = root / name
        profile_dir.mkdir()
        (profile_dir / "Preferences").write_text("{}", encoding="utf-8")
    (root / "System Profile").mkdir()
    (root / "System Profile" / "Preferences").write_text("{}", encoding="utf-8")
    (root / "Crash Reports").mkdir()
    return root


@pytest.fixture
def profiles() -> list[Profile]:
    return [
        Profile(id="Default", directory_name="Default", brave_display_name="Alice Doe"),
        Profile(id="Profile 1", directory_name="Profile 1", brave_display_name="Work"),
    ]


@pytest.fixture
def windows() -> list[WindowInfo]:
    return [
        WindowInfo(window_id=0x1001, pid=42, title="Ejemplo"),
        WindowInfo(window_id=0x1002, pid=42, title="Otro"),
    ]
