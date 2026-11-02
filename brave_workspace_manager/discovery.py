"""Non-destructive discovery of the native Brave profiles."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

IGNORED_PROFILES = {"System Profile", "Guest Profile"}


@dataclass(slots=True)
class DiscoveredProfile:
    directory_name: str
    display_name: str
    avatar_path: str | None = None
    active_time: float | None = None


def read_local_state(user_data_dir: Path) -> dict:
    """Reads Local State tolerating errors; it never writes to the profile."""
    path = Path(user_data_dir) / "Local State"
    try:
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def profile_sort_key(name: str) -> tuple:
    if name == "Default":
        return (0, 0, "")
    if name.startswith("Profile "):
        tail = name.split(" ", 1)[1]
        if tail.isdigit():
            return (1, int(tail), name)
    return (2, 0, name)


def profile_directories(user_data_dir: Path) -> list[str]:
    """Real profile folders: those that contain a Preferences file."""
    names: list[str] = []
    try:
        entries = sorted(Path(user_data_dir).iterdir())
    except OSError:
        return names
    for entry in entries:
        if not entry.is_dir() or entry.name in IGNORED_PROFILES:
            continue
        if (entry / "Preferences").is_file():
            names.append(entry.name)
    return sorted(names, key=profile_sort_key)


def prettify_directory(name: str) -> str:
    if name == "Default":
        return "Default"
    if name.startswith("Profile "):
        return name
    return name.replace("_", " ").replace("-", " ").strip().title()


def _avatar_path(user_data_dir: Path, raw: object) -> str | None:
    if not isinstance(raw, str) or not raw:
        return None
    candidate = Path(raw)
    if not candidate.is_absolute():
        candidate = Path(user_data_dir) / raw
    try:
        if candidate.exists():
            return str(candidate)
    except OSError:
        return None
    return None


def discover_profiles(user_data_dir: Path) -> list[DiscoveredProfile]:
    """Existing profiles with their visible name, as Brave shows them."""
    user_data_dir = Path(user_data_dir)
    state = read_local_state(user_data_dir)
    profile_state = state.get("profile")
    profile_state = profile_state if isinstance(profile_state, dict) else {}
    info_cache = profile_state.get("info_cache")
    info_cache = info_cache if isinstance(info_cache, dict) else {}

    discovered: list[DiscoveredProfile] = []
    for directory_name in profile_directories(user_data_dir):
        info = info_cache.get(directory_name)
        info = info if isinstance(info, dict) else {}
        name = str(info.get("name") or "").strip()
        gaia = str(info.get("gaia_name") or "").strip()
        display = name or gaia or prettify_directory(directory_name)
        active_time = info.get("active_time")
        discovered.append(
            DiscoveredProfile(
                directory_name=directory_name,
                display_name=display,
                avatar_path=_avatar_path(user_data_dir, info.get("avatar_icon")),
                active_time=float(active_time) if isinstance(active_time, (int, float)) else None,
            )
        )
    return discovered


def last_used_profile(user_data_dir: Path) -> str | None:
    state = read_local_state(user_data_dir)
    profile_state = state.get("profile")
    profile_state = profile_state if isinstance(profile_state, dict) else {}
    value = profile_state.get("last_used")
    return value if isinstance(value, str) else None


def last_active_profiles(user_data_dir: Path) -> list[str]:
    state = read_local_state(user_data_dir)
    profile_state = state.get("profile")
    profile_state = profile_state if isinstance(profile_state, dict) else {}
    value = profile_state.get("last_active_profiles")
    if isinstance(value, list):
        return [item for item in value if isinstance(item, str)]
    return []
