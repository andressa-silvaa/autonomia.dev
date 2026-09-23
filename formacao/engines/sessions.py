from __future__ import annotations

import sqlite3
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timedelta

from formacao.core.clock import local_date_of, parse_iso_utc, to_iso_utc
from formacao.engines.content import module_key

SECONDS_PER_MINUTE = 60


class ActiveSessionExistsError(Exception):
    def __init__(self, session: SessionView) -> None:
        super().__init__(f"Session {session.id} is already running")
        self.session = session


class NoActiveSessionError(Exception):
    pass


@dataclass(frozen=True, slots=True)
class SessionView:
    id: int
    module_key: str | None
    module_title: str | None
    started_at: datetime
    ended_at: datetime | None
    notes: str

    def duration(self, now: datetime) -> timedelta:
        return (self.ended_at or now) - self.started_at

    def elapsed_minutes(self, now: datetime) -> int:
        return int(self.duration(now).total_seconds() // SECONDS_PER_MINUTE)


_SESSION_SELECT = (
    "SELECT study_sessions.id, study_sessions.started_at, study_sessions.ended_at, "
    "study_sessions.notes, modules.slug AS module_slug, modules.title AS module_title, "
    "tracks.slug AS track_slug "
    "FROM study_sessions "
    "LEFT JOIN modules ON modules.id = study_sessions.module_id "
    "LEFT JOIN tracks ON tracks.id = modules.track_id "
)


def _row_to_session(row: sqlite3.Row) -> SessionView:
    has_module = row["module_slug"] is not None
    return SessionView(
        id=row["id"],
        module_key=module_key(row["track_slug"], row["module_slug"]) if has_module else None,
        module_title=row["module_title"],
        started_at=parse_iso_utc(row["started_at"]),
        ended_at=parse_iso_utc(row["ended_at"]) if row["ended_at"] else None,
        notes=row["notes"],
    )


def _get_session(conn: sqlite3.Connection, session_id: int) -> SessionView:
    row = conn.execute(_SESSION_SELECT + "WHERE study_sessions.id = ?", (session_id,)).fetchone()
    return _row_to_session(row)


def find_active_session(conn: sqlite3.Connection, user_id: int) -> SessionView | None:
    row = conn.execute(
        _SESSION_SELECT + "WHERE study_sessions.user_id = ? AND study_sessions.ended_at IS NULL",
        (user_id,),
    ).fetchone()
    return _row_to_session(row) if row is not None else None


def start_session(
    conn: sqlite3.Connection, user_id: int, module_id: int | None, now: datetime
) -> SessionView:
    active = find_active_session(conn, user_id)
    if active is not None:
        raise ActiveSessionExistsError(active)
    with conn:
        cursor = conn.execute(
            "INSERT INTO study_sessions (user_id, module_id, started_at) VALUES (?, ?, ?)",
            (user_id, module_id, to_iso_utc(now)),
        )
    return _get_session(conn, cursor.lastrowid)


def stop_session(conn: sqlite3.Connection, user_id: int, notes: str, now: datetime) -> SessionView:
    active = find_active_session(conn, user_id)
    if active is None:
        raise NoActiveSessionError("No study session is running")
    ended_at = max(now, active.started_at)
    with conn:
        conn.execute(
            "UPDATE study_sessions SET ended_at = ?, notes = ? WHERE id = ?",
            (to_iso_utc(ended_at), notes.strip(), active.id),
        )
    return _get_session(conn, active.id)


def study_minutes_by_day(
    conn: sqlite3.Connection, user_id: int, first_day: date, last_day: date, now: datetime
) -> list[tuple[date, int]]:
    search_start = datetime.combine(first_day - timedelta(days=1), datetime.min.time()).astimezone()
    rows = conn.execute(
        _SESSION_SELECT + "WHERE study_sessions.user_id = ? AND study_sessions.started_at >= ?",
        (user_id, to_iso_utc(search_start)),
    )

    seconds_by_day: dict[date, float] = defaultdict(float)
    for session in map(_row_to_session, rows):
        seconds_by_day[local_date_of(session.started_at)] += session.duration(now).total_seconds()

    day_count = (last_day - first_day).days + 1
    days = [first_day + timedelta(days=offset) for offset in range(day_count)]
    return [(day, round(seconds_by_day[day] / SECONDS_PER_MINUTE)) for day in days]
