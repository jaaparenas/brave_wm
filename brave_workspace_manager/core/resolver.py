"""Matching of Brave windows with the native profiles that own them.

Chromium runs every window of every profile of a user-data-dir inside a single
browser process, so the PID of a window does not identify its profile and no
standard X11 property reveals it. The window title is the title of the active
page, so it says nothing reliable about the profile (a page may mention any
profile name). The match is therefore resolved by combining:

* assignments learned in previous runs (persisted),
* the only open profile when just one is active,
* elimination: when a single unassigned window and a single open profile
  without windows remain, they belong together.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..models import MatchMethod, Profile, WindowInfo


@dataclass
class ResolutionContext:
    profiles: list[Profile]
    windows: list[WindowInfo]
    open_profile_ids: set[str] = field(default_factory=set)
    assignments: dict[tuple[int, int], dict] = field(default_factory=dict)


class WindowResolver:
    """Assigns every Brave window to its most likely profile."""

    def resolve(self, context: ResolutionContext) -> dict[int, MatchMethod]:
        windows = context.windows
        assigned: dict[int, MatchMethod] = {}

        for window in windows:
            row = context.assignments.get((window.window_id, window.pid))
            if row and row.get("profile_id"):
                window.profile_id = row["profile_id"]
                method = MatchMethod(row.get("method") or MatchMethod.LEARNED)
                if method not in (MatchMethod.LEARNED, MatchMethod.MANUAL):
                    method = MatchMethod.LEARNED
                window.method = method
                window.confidence = 1.0
                assigned[window.window_id] = method

        self._apply_single_open_profile(context, assigned)
        self._apply_elimination(context, assigned)

        for window in windows:
            if window.window_id not in assigned:
                window.profile_id = None
                window.method = MatchMethod.NONE
                window.confidence = 0.0
        return assigned

    # ---------------------------------------------------------------- reglas

    def _apply_single_open_profile(
        self, context: ResolutionContext, assigned: dict[int, MatchMethod]
    ) -> None:
        if len(context.open_profile_ids) != 1:
            return
        only = next(iter(context.open_profile_ids))
        for window in context.windows:
            if window.window_id in assigned:
                continue
            window.profile_id = only
            window.method = MatchMethod.SINGLE_PROFILE
            window.confidence = 0.9
            assigned[window.window_id] = MatchMethod.SINGLE_PROFILE

    def _apply_elimination(
        self, context: ResolutionContext, assigned: dict[int, MatchMethod]
    ) -> None:
        unassigned_windows = [w for w in context.windows if w.window_id not in assigned]
        if len(unassigned_windows) != 1:
            return
        used_profiles = {
            w.profile_id for w in context.windows if w.profile_id and w.window_id in assigned
        }
        candidates = [
            profile
            for profile in context.profiles
            if profile.id in context.open_profile_ids and profile.id not in used_profiles
        ]
        if len(candidates) != 1:
            return
        window = unassigned_windows[0]
        window.profile_id = candidates[0].id
        window.method = MatchMethod.ELIMINATION
        window.confidence = 0.5
        assigned[window.window_id] = MatchMethod.ELIMINATION
