from __future__ import annotations

import sqlite3
from datetime import UTC, date, datetime, timedelta

import pytest

from formacao.core.clock import local_date_of
from formacao.engines.checkins import (
    AlreadyCheckedInError,
    EmptyIntentionError,
    check_in,
    compute_streak,
    get_streak,
)
from formacao.engines.sessions import (
    ActiveSessionExistsError,
    NoActiveSessionError,
    find_active_session,
    start_session,
    stop_session,
    study_minutes_by_day,
)

NOW = datetime(2026, 9, 23, 15, 0, tzinfo=UTC)
TODAY = date(2026, 9, 23)


def _days(*offsets: int) -> set[date]:
    return {TODAY - timedelta(days=offset) for offset in offsets}


def test_session_lifecycle(conn: sqlite3.Connection, user_id: int) -> None:
    start_session(conn, user_id, None, NOW)
    assert find_active_session(conn, user_id) is not None

    with pytest.raises(ActiveSessionExistsError):
        start_session(conn, user_id, None, NOW)

    stopped = stop_session(conn, user_id, "  li sobre recursão  ", NOW + timedelta(minutes=40))
    assert stopped.notes == "li sobre recursão"
    assert stopped.duration(NOW) == timedelta(minutes=40)
    assert find_active_session(conn, user_id) is None

    with pytest.raises(NoActiveSessionError):
        stop_session(conn, user_id, "", NOW)


def test_database_enforces_single_active_session(conn: sqlite3.Connection, user_id: int) -> None:
    conn.execute("INSERT INTO study_sessions (user_id) VALUES (?)", (user_id,))
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("INSERT INTO study_sessions (user_id) VALUES (?)", (user_id,))


def test_study_minutes_by_day_includes_running_session(
    conn: sqlite3.Connection, user_id: int
) -> None:
    start_session(conn, user_id, None, NOW - timedelta(minutes=30))
    stop_session(conn, user_id, "", NOW - timedelta(minutes=5))
    start_session(conn, user_id, None, NOW - timedelta(minutes=10))

    study_day = local_date_of(NOW)
    minutes = dict(
        study_minutes_by_day(conn, user_id, study_day - timedelta(days=2), study_day, NOW)
    )
    assert minutes[study_day] == 35
    assert minutes[study_day - timedelta(days=1)] == 0
    assert len(minutes) == 3


def test_check_in_once_per_day(conn: sqlite3.Connection, user_id: int) -> None:
    check_in(conn, user_id, "Big-O", TODAY, NOW)
    with pytest.raises(AlreadyCheckedInError) as caught:
        check_in(conn, user_id, "outra coisa", TODAY, NOW)
    assert caught.value.checkin.intention == "Big-O"
    with pytest.raises(EmptyIntentionError):
        check_in(conn, user_id, "   ", TODAY + timedelta(days=1), NOW)


def test_get_streak_reads_from_database(conn: sqlite3.Connection, user_id: int) -> None:
    for offset in (2, 1, 0):
        check_in(conn, user_id, "estudar", TODAY - timedelta(days=offset), NOW)
    streak = get_streak(conn, user_id, TODAY)
    assert (streak.current, streak.longest, streak.checked_in_today) == (3, 3, True)


@pytest.mark.parametrize(
    ("days", "expected"),
    [
        (set(), (0, 0, False)),
        (_days(0), (1, 1, True)),
        (_days(1, 2, 3), (3, 3, False)),
        (_days(0, 1, 2), (3, 3, True)),
        (_days(2, 3), (0, 2, False)),
        (_days(0, 5, 6, 7, 8), (1, 4, True)),
    ],
)
def test_compute_streak(days: set[date], expected: tuple[int, int, bool]) -> None:
    streak = compute_streak(days, TODAY)
    assert (streak.current, streak.longest, streak.checked_in_today) == expected
