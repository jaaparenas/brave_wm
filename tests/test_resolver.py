"""Tests of the matching between windows and profiles."""

from __future__ import annotations

from brave_workspace_manager.core.resolver import ResolutionContext, WindowResolver
from brave_workspace_manager.models import MatchMethod


def _context(profiles, windows, open_ids=(), assignments=None) -> ResolutionContext:
    return ResolutionContext(
        profiles=profiles,
        windows=windows,
        open_profile_ids=set(open_ids),
        assignments=assignments or {},
    )


def test_learned_assignment_wins(profiles, windows) -> None:
    context = _context(
        profiles,
        windows,
        open_ids={"Default", "Profile 1"},
        assignments={(0x1001, 42): {"profile_id": "Profile 1", "method": "learned"}},
    )
    WindowResolver().resolve(context)
    assert windows[0].profile_id == "Profile 1"
    assert windows[0].method == MatchMethod.LEARNED
    assert windows[0].confidence == 1.0


def test_single_open_profile_claims_every_window(profiles, windows) -> None:
    context = _context(profiles, windows, open_ids={"Profile 1"})
    WindowResolver().resolve(context)
    assert [w.profile_id for w in windows] == ["Profile 1", "Profile 1"]
    assert windows[0].method == MatchMethod.SINGLE_PROFILE


def test_no_assignment_when_several_profiles_are_open(profiles, windows) -> None:
    context = _context(profiles, windows, open_ids={"Default", "Profile 1"})
    WindowResolver().resolve(context)
    assert [w.profile_id for w in windows] == [None, None]
    assert all(w.method == MatchMethod.NONE for w in windows)


def test_elimination_assigns_the_last_window(profiles, windows) -> None:
    """With two open profiles, the free window belongs to the one without windows."""
    context = _context(profiles, windows, open_ids={"Default", "Profile 1"})
    context.assignments = {(0x1001, 42): {"profile_id": "Default", "method": "learned"}}
    WindowResolver().resolve(context)
    assert windows[0].profile_id == "Default"
    assert windows[1].profile_id == "Profile 1"
    assert windows[1].method == MatchMethod.ELIMINATION


def test_title_match_is_used_when_possible(profiles, windows) -> None:
    windows[0].title = "Work · Panel de control"
    context = _context(profiles, windows, open_ids={"Default", "Profile 1"})
    WindowResolver().resolve(context)
    assert windows[0].profile_id == "Profile 1"
    assert windows[0].method == MatchMethod.TITLE


def test_title_match_requires_whole_words(profiles, windows) -> None:
    windows[0].title = "Informe WorkX del trimestre"
    context = _context(profiles, windows, open_ids={"Default", "Profile 1"})
    WindowResolver().resolve(context)
    assert windows[0].profile_id is None


def test_manual_assignment_is_not_downgraded(profiles, windows) -> None:
    context = _context(
        profiles,
        windows,
        open_ids={"Default"},
        assignments={(0x1001, 42): {"profile_id": "Profile 1", "method": "manual"}},
    )
    WindowResolver().resolve(context)
    assert windows[0].profile_id == "Profile 1"
    assert windows[0].method == MatchMethod.MANUAL


def test_resolver_is_idempotent(profiles, windows) -> None:
    context = _context(profiles, windows, open_ids={"Default"})
    resolver = WindowResolver()
    resolver.resolve(context)
    first = [w.profile_id for w in windows]
    resolver.resolve(context)
    assert [w.profile_id for w in windows] == first
