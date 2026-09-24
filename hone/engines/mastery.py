from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime

from hone.core.clock import to_iso_utc
from hone.core.models import Mastery


@dataclass(frozen=True, slots=True)
class MasteryChange:
    competency_id: int
    before: Mastery
    after: Mastery


def masteries_by_competency(conn: sqlite3.Connection, user_id: int) -> dict[int, Mastery]:
    rows = conn.execute(
        "SELECT competencies.id, user_competencies.mastery FROM competencies "
        "LEFT JOIN user_competencies ON user_competencies.competency_id = competencies.id "
        "AND user_competencies.user_id = ?",
        (user_id,),
    )
    return {row["id"]: Mastery(row["mastery"] or Mastery.NOT_STUDIED) for row in rows}


def current_mastery(conn: sqlite3.Connection, user_id: int, competency_id: int) -> Mastery:
    row = conn.execute(
        "SELECT mastery FROM user_competencies WHERE user_id = ? AND competency_id = ?",
        (user_id, competency_id),
    ).fetchone()
    return Mastery(row["mastery"]) if row is not None else Mastery.NOT_STUDIED


def record_mastery(
    conn: sqlite3.Connection,
    user_id: int,
    competency_id: int,
    mastery: Mastery,
    source: str,
    source_id: int | None,
    now: datetime,
) -> MasteryChange | None:
    before = current_mastery(conn, user_id, competency_id)
    if before is mastery:
        return None

    timestamp = to_iso_utc(now)
    conn.execute(
        "INSERT INTO user_competencies (user_id, competency_id, mastery, updated_at) "
        "VALUES (?, ?, ?, ?) ON CONFLICT (user_id, competency_id) DO UPDATE SET "
        "mastery = excluded.mastery, updated_at = excluded.updated_at",
        (user_id, competency_id, mastery, timestamp),
    )
    conn.execute(
        "INSERT INTO mastery_events "
        "(user_id, competency_id, from_mastery, to_mastery, source, source_id, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (user_id, competency_id, before, mastery, source, source_id, timestamp),
    )
    return MasteryChange(competency_id, before, mastery)
