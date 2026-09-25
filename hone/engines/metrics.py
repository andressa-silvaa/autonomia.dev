from __future__ import annotations

import sqlite3
from collections import defaultdict
from dataclasses import dataclass

from hone.engines.xp import XpTotals, xp_totals


@dataclass(frozen=True, slots=True)
class ExerciseAttempts:
    count: int
    passed_on_first_try: bool
    hints_used: int
    ai_attempts: int


@dataclass(frozen=True, slots=True)
class CompetencyPractice:
    competency_id: int
    name: str
    exercises_total: int
    exercises_passed: int
    first_try_passes: int
    attempts: int
    hints_used: int
    ai_attempts: int

    @property
    def first_try_rate(self) -> float | None:
        return self.first_try_passes / self.exercises_passed if self.exercises_passed else None


@dataclass(frozen=True, slots=True)
class PracticeStats:
    xp: XpTotals
    competencies: tuple[CompetencyPractice, ...]

    @property
    def exercises_passed(self) -> int:
        return sum(item.exercises_passed for item in self.competencies)


def _attempts_by_exercise(conn: sqlite3.Connection, user_id: int) -> dict[int, ExerciseAttempts]:
    grouped: dict[int, list[sqlite3.Row]] = defaultdict(list)
    for row in conn.execute(
        "SELECT exercise_id, passed, hints_used, used_ai FROM attempts "
        "WHERE user_id = ? ORDER BY submitted_at, id",
        (user_id,),
    ):
        grouped[row["exercise_id"]].append(row)
    return {
        exercise_id: ExerciseAttempts(
            count=len(rows),
            passed_on_first_try=bool(rows[0]["passed"]),
            hints_used=max(row["hints_used"] for row in rows),
            ai_attempts=sum(row["used_ai"] for row in rows),
        )
        for exercise_id, rows in grouped.items()
    }


def build_practice_stats(conn: sqlite3.Connection, user_id: int) -> PracticeStats:
    attempts = _attempts_by_exercise(conn, user_id)
    names: dict[int, str] = {}
    exercises_by_competency: dict[int, list[tuple[int, bool]]] = defaultdict(list)
    for row in conn.execute(
        "SELECT competencies.id AS competency_id, competencies.name, exercises.id AS exercise_id, "
        "exercise_progress.passed_at FROM competencies "
        "JOIN module_competencies ON module_competencies.competency_id = competencies.id "
        "JOIN exercises ON exercises.module_id = module_competencies.module_id "
        "AND exercises.retired = 0 "
        "LEFT JOIN exercise_progress ON exercise_progress.exercise_id = exercises.id "
        "AND exercise_progress.user_id = ? "
        "ORDER BY competencies.id, exercises.position",
        (user_id,),
    ):
        names[row["competency_id"]] = row["name"]
        exercises_by_competency[row["competency_id"]].append(
            (row["exercise_id"], row["passed_at"] is not None)
        )

    empty = ExerciseAttempts(0, False, 0, 0)
    competencies = []
    for competency_id, exercises in exercises_by_competency.items():
        history = [(attempts.get(exercise_id, empty), passed) for exercise_id, passed in exercises]
        competencies.append(
            CompetencyPractice(
                competency_id=competency_id,
                name=names[competency_id],
                exercises_total=len(exercises),
                exercises_passed=sum(passed for _, passed in history),
                first_try_passes=sum(record.passed_on_first_try for record, _ in history),
                attempts=sum(record.count for record, _ in history),
                hints_used=sum(record.hints_used for record, _ in history),
                ai_attempts=sum(record.ai_attempts for record, _ in history),
            )
        )
    return PracticeStats(xp_totals(conn, user_id), tuple(competencies))
