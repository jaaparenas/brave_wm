"""SQLite persistence: profiles, window assignments and settings."""

from __future__ import annotations

import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path

from .models import Profile

_SCHEMA = """
CREATE TABLE IF NOT EXISTS profiles (
    id             TEXT PRIMARY KEY,
    directory_name TEXT NOT NULL,
    display_name   TEXT NOT NULL DEFAULT '',
    color          TEXT NOT NULL DEFAULT '#4f8cff',
    icon           TEXT NOT NULL DEFAULT 'circle',
    sort_order     INTEGER NOT NULL DEFAULT 0,
    is_favorite    INTEGER NOT NULL DEFAULT 0,
    created_at     TEXT NOT NULL,
    updated_at     TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS window_assignments (
    window_id   INTEGER NOT NULL,
    browser_pid INTEGER NOT NULL,
    profile_id  TEXT NOT NULL,
    title       TEXT NOT NULL DEFAULT '',
    method      TEXT NOT NULL DEFAULT 'learned',
    updated_at  TEXT NOT NULL,
    PRIMARY KEY (window_id, browser_pid)
);

CREATE TABLE IF NOT EXISTS settings (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""


def utc_timestamp() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


class Database:
    """Thread-safe access to the local database of the application."""

    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._conn = sqlite3.connect(self.path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self.migrate()

    def close(self) -> None:
        with self._lock:
            self._conn.close()

    def migrate(self) -> None:
        with self._lock, self._conn:
            self._conn.executescript(_SCHEMA)
            self._add_missing_columns()

    def _add_missing_columns(self) -> None:
        """Adds the columns introduced after the first release."""
        columns = {
            row["name"] for row in self._conn.execute("PRAGMA table_info(profiles)").fetchall()
        }
        for name, definition in (
            ("custom_image", "TEXT NOT NULL DEFAULT ''"),
            ("is_virtual", "INTEGER NOT NULL DEFAULT 0"),
        ):
            if name not in columns:
                self._conn.execute(f"ALTER TABLE profiles ADD COLUMN {name} {definition}")

    # ------------------------------------------------------------------ profiles

    def load_profiles(self) -> dict[str, Profile]:
        with self._lock:
            rows = self._conn.execute("SELECT * FROM profiles").fetchall()
        profiles: dict[str, Profile] = {}
        for row in rows:
            profiles[row["id"]] = Profile(
                id=row["id"],
                directory_name=row["directory_name"],
                display_name=row["display_name"],
                color=row["color"],
                icon=row["icon"],
                sort_order=row["sort_order"],
                is_favorite=bool(row["is_favorite"]),
                custom_image=row["custom_image"] or "",
                is_virtual=bool(row["is_virtual"]),
                custom=True,
            )
        return profiles

    def save_profile(self, profile: Profile) -> None:
        stamp = utc_timestamp()
        with self._lock, self._conn:
            self._conn.execute(
                """
                INSERT INTO profiles (id, directory_name, display_name, color, icon,
                                      sort_order, is_favorite, custom_image, is_virtual,
                                      created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    display_name = excluded.display_name,
                    color = excluded.color,
                    icon = excluded.icon,
                    sort_order = excluded.sort_order,
                    is_favorite = excluded.is_favorite,
                    custom_image = excluded.custom_image,
                    is_virtual = excluded.is_virtual,
                    updated_at = excluded.updated_at
                """,
                (
                    profile.id,
                    profile.directory_name,
                    profile.display_name,
                    profile.color,
                    profile.icon,
                    profile.sort_order,
                    int(profile.is_favorite),
                    profile.custom_image,
                    int(profile.is_virtual),
                    stamp,
                    stamp,
                ),
            )

    def delete_profile(self, profile_id: str) -> None:
        with self._lock, self._conn:
            self._conn.execute("DELETE FROM profiles WHERE id = ?", (profile_id,))
            self._conn.execute("DELETE FROM window_assignments WHERE profile_id = ?", (profile_id,))

    def next_sort_order(self) -> int:
        with self._lock:
            row = self._conn.execute("SELECT MAX(sort_order) AS value FROM profiles").fetchone()
        current = row["value"] if row and row["value"] is not None else -1
        return int(current) + 1

    # ----------------------------------------------------------------- ajustes

    def get_setting(self, key: str, default: str | None = None) -> str | None:
        with self._lock:
            row = self._conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
        return row["value"] if row else default

    def set_setting(self, key: str, value: str) -> None:
        with self._lock, self._conn:
            self._conn.execute(
                "INSERT INTO settings (key, value) VALUES (?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                (key, value),
            )

    # ------------------------------------------------------- asignaciones

    def assign_window(
        self,
        window_id: int,
        browser_pid: int,
        profile_id: str,
        title: str = "",
        method: str = "learned",
    ) -> None:
        with self._lock, self._conn:
            self._conn.execute(
                """
                INSERT INTO window_assignments (window_id, browser_pid, profile_id, title, method, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(window_id, browser_pid) DO UPDATE SET
                    profile_id = excluded.profile_id,
                    title = excluded.title,
                    method = excluded.method,
                    updated_at = excluded.updated_at
                """,
                (window_id, browser_pid, profile_id, title, method, utc_timestamp()),
            )

    def unassign_window(self, window_id: int, browser_pid: int) -> None:
        with self._lock, self._conn:
            self._conn.execute(
                "DELETE FROM window_assignments WHERE window_id = ? AND browser_pid = ?",
                (window_id, browser_pid),
            )

    def load_assignments(self) -> dict[tuple[int, int], dict]:
        with self._lock:
            rows = self._conn.execute("SELECT * FROM window_assignments").fetchall()
        return {(row["window_id"], row["browser_pid"]): dict(row) for row in rows}

    def clear_assignments(self, browser_pid: int | None = None) -> None:
        with self._lock, self._conn:
            if browser_pid is None:
                self._conn.execute("DELETE FROM window_assignments")
            else:
                self._conn.execute(
                    "DELETE FROM window_assignments WHERE browser_pid = ?", (browser_pid,)
                )
