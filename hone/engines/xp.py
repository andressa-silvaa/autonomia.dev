from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime

from hone.core.clock import to_iso_utc
from hone.core.models import AnswerFormat, GradingMethod, XpKind

ATTEMPT_SOURCE = "attempt"
ACTIVITY_XP_PER_ATTEMPT = 2
MAX_REWARDED_ATTEMPTS_PER_EXERCISE = 3
HINT_XP_PENALTY = 0.25
MIN_XP_SHARE = 0.25
SELF_GRADED_XP_WEIGHT = 0.5
FORMAT_XP_WEIGHT = {
    AnswerFormat.CHOICE: 0.5,
    AnswerFormat.TYPED: 0.5,
    AnswerFormat.CODE: 1.0,
    AnswerFormat.TEXT: 1.0,
}


@dataclass(frozen=True, slots=True)
class XpTotals:
    competency: int
    activity: int


def competency_xp(
    base_xp: int, answer_format: AnswerFormat, graded_by: GradingMethod, hints_used: int
) -> int:
    weight = FORMAT_XP_WEIGHT[answer_format]
    if graded_by is GradingMethod.SELF_ASSESSMENT:
        weight *= SELF_GRADED_XP_WEIGHT
    hint_share = max(MIN_XP_SHARE, 1 - HINT_XP_PENALTY * hints_used)
    return round(base_xp * weight * hint_share)


def activity_xp(previous_attempts: int) -> int:
    return ACTIVITY_XP_PER_ATTEMPT if previous_attempts < MAX_REWARDED_ATTEMPTS_PER_EXERCISE else 0


def grant_xp(
    conn: sqlite3.Connection,
    user_id: int,
    kind: XpKind,
    amount: int,
    source_id: int,
    now: datetime,
) -> None:
    if amount <= 0:
        return
    conn.execute(
        "INSERT INTO xp_events (user_id, kind, amount, source, source_id, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (user_id, kind, amount, ATTEMPT_SOURCE, source_id, to_iso_utc(now)),
    )


def xp_totals(conn: sqlite3.Connection, user_id: int) -> XpTotals:
    totals = dict.fromkeys(XpKind, 0)
    for row in conn.execute(
        "SELECT kind, SUM(amount) AS total FROM xp_events WHERE user_id = ? GROUP BY kind",
        (user_id,),
    ):
        totals[XpKind(row["kind"])] = row["total"]
    return XpTotals(totals[XpKind.COMPETENCY], totals[XpKind.ACTIVITY])
