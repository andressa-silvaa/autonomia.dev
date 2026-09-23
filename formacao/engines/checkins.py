from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import date, datetime, timedelta

from formacao.core.clock import to_iso_utc

ONE_DAY = timedelta(days=1)


class AlreadyCheckedInError(Exception):
    def __init__(self, checkin: Checkin) -> None:
        super().__init__(f"Already checked in on {checkin.day.isoformat()}")
        self.checkin = checkin


class EmptyIntentionError(Exception):
    pass


@dataclass(frozen=True, slots=True)
class Checkin:
    day: date
    intention: str


@dataclass(frozen=True, slots=True)
class Streak:
    current: int
    longest: int
    checked_in_today: bool


def find_checkin(conn: sqlite3.Connection, user_id: int, day: date) -> Checkin | None:
    row = conn.execute(
        "SELECT day, intention FROM checkins WHERE user_id = ? AND day = ?",
        (user_id, day.isoformat()),
    ).fetchone()
    return Checkin(date.fromisoformat(row["day"]), row["intention"]) if row is not None else None


def check_in(
    conn: sqlite3.Connection, user_id: int, intention: str, today: date, now: datetime
) -> Checkin:
    intention = intention.strip()
    if not intention:
        raise EmptyIntentionError("Intention must not be empty")
    existing = find_checkin(conn, user_id, today)
    if existing is not None:
        raise AlreadyCheckedInError(existing)
    with conn:
        conn.execute(
            "INSERT INTO checkins (user_id, day, intention, created_at) VALUES (?, ?, ?, ?)",
            (user_id, today.isoformat(), intention, to_iso_utc(now)),
        )
    return Checkin(today, intention)


def _count_consecutive_days_until(days: set[date], last_day: date) -> int:
    count = 0
    while last_day - count * ONE_DAY in days:
        count += 1
    return count


def _longest_run(days: set[date]) -> int:
    longest = 0
    for day in days:
        starts_a_run = day - ONE_DAY not in days
        if starts_a_run:
            length = 1
            while day + length * ONE_DAY in days:
                length += 1
            longest = max(longest, length)
    return longest


def compute_streak(days: set[date], today: date) -> Streak:
    checked_in_today = today in days
    streak_end = today if checked_in_today else today - ONE_DAY
    return Streak(
        current=_count_consecutive_days_until(days, streak_end),
        longest=_longest_run(days),
        checked_in_today=checked_in_today,
    )


def get_streak(conn: sqlite3.Connection, user_id: int, today: date) -> Streak:
    rows = conn.execute("SELECT day FROM checkins WHERE user_id = ?", (user_id,))
    return compute_streak({date.fromisoformat(row["day"]) for row in rows}, today)
