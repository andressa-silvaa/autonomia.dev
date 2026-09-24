from __future__ import annotations

import sqlite3
from datetime import UTC, datetime

import pytest

from hone.engines.progress import (
    AmbiguousModuleError,
    ModuleLockedError,
    ModuleStatus,
    UnknownModuleError,
    complete_module,
    find_track_view,
    resolve_module,
    start_module,
)

NOW = datetime(2026, 9, 23, 12, 0, tzinfo=UTC)


def _statuses(conn: sqlite3.Connection, user_id: int) -> dict[str, ModuleStatus]:
    track = find_track_view(conn, user_id, "sample")
    assert track is not None
    return {module.slug: module.status for module in track.modules}


def test_only_modules_without_prerequisites_start_available(
    synced: sqlite3.Connection, user_id: int
) -> None:
    assert _statuses(synced, user_id) == {
        "first": ModuleStatus.AVAILABLE,
        "second": ModuleStatus.LOCKED,
        "third": ModuleStatus.LOCKED,
    }


def test_locked_module_cannot_be_started_or_completed(
    synced: sqlite3.Connection, user_id: int
) -> None:
    second = resolve_module(synced, user_id, "second")
    with pytest.raises(ModuleLockedError) as caught:
        start_module(synced, user_id, second, NOW)
    assert [link.key for link in caught.value.module.missing_prerequisites] == ["sample/first"]
    with pytest.raises(ModuleLockedError):
        complete_module(synced, user_id, second, NOW)


def test_completing_unlocks_only_modules_whose_prerequisites_are_all_done(
    synced: sqlite3.Connection, user_id: int
) -> None:
    start_module(synced, user_id, resolve_module(synced, user_id, "first"), NOW)
    assert _statuses(synced, user_id)["first"] is ModuleStatus.IN_PROGRESS

    unlocked = complete_module(synced, user_id, resolve_module(synced, user_id, "first"), NOW)
    assert [module.slug for module in unlocked] == ["second"]

    unlocked = complete_module(synced, user_id, resolve_module(synced, user_id, "second"), NOW)
    assert [module.slug for module in unlocked] == ["third"]


def test_completing_twice_is_harmless(synced: sqlite3.Connection, user_id: int) -> None:
    first = resolve_module(synced, user_id, "first")
    complete_module(synced, user_id, first, NOW)
    again = resolve_module(synced, user_id, "first")
    assert complete_module(synced, user_id, again, NOW) == []


def test_track_view_counts_progress(synced: sqlite3.Connection, user_id: int) -> None:
    complete_module(synced, user_id, resolve_module(synced, user_id, "first"), NOW)
    track = find_track_view(synced, user_id, "sample")
    assert track is not None
    assert (track.completed_count, track.total_count, track.is_complete) == (1, 3, False)


def test_resolve_accepts_qualified_and_short_references(
    synced: sqlite3.Connection, user_id: int
) -> None:
    assert resolve_module(synced, user_id, "sample/first").slug == "first"
    assert resolve_module(synced, user_id, "first").key == "sample/first"
    with pytest.raises(UnknownModuleError):
        resolve_module(synced, user_id, "nope")


def test_resolve_rejects_ambiguous_short_reference(
    synced: sqlite3.Connection, user_id: int
) -> None:
    other_track = synced.execute(
        "INSERT INTO tracks (slug, name) VALUES ('other', 'Outra')"
    ).lastrowid
    synced.execute(
        "INSERT INTO modules (track_id, slug, title) VALUES (?, 'first', 'Outro primeiro')",
        (other_track,),
    )
    with pytest.raises(AmbiguousModuleError) as caught:
        resolve_module(synced, user_id, "first")
    assert sorted(caught.value.candidates) == ["other/first", "sample/first"]
