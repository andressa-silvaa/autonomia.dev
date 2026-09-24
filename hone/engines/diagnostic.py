from __future__ import annotations

import json
import sqlite3
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime

from hone.core.clock import parse_iso_utc, to_iso_utc
from hone.core.models import AnswerConfidence, Mastery, QuestionKind
from hone.engines.mastery import current_mastery, record_mastery

DIAGNOSTIC_SOURCE = "diagnostic"
DIAGNOSTIC_CEILING = Mastery.CAN_APPLY
MIN_SURE_CORRECT_SHARE = 0.5


class NoQuestionsError(Exception):
    def __init__(self) -> None:
        super().__init__("No diagnostic questions loaded")


class NoFinishedDiagnosticError(Exception):
    def __init__(self) -> None:
        super().__init__("No finished diagnostic yet")


class NoOpenDiagnosticError(Exception):
    def __init__(self) -> None:
        super().__init__("No diagnostic in progress")


class DiagnosticIncompleteError(Exception):
    def __init__(self, remaining: int) -> None:
        super().__init__(f"Diagnostic still has {remaining} unanswered question(s)")
        self.remaining = remaining


@dataclass(frozen=True, slots=True)
class Question:
    id: int
    slug: str
    competency_id: int
    competency_name: str
    kind: QuestionKind
    prompt: str
    options: tuple[str, ...]
    accepted_answers: tuple[str, ...]
    explanation: str

    @property
    def is_choice(self) -> bool:
        return bool(self.options)

    @property
    def correct_answer(self) -> str:
        return self.accepted_answers[0]


@dataclass(frozen=True, slots=True)
class DiagnosticRun:
    id: int
    started_at: datetime
    finished_at: datetime | None
    answered_count: int
    total_count: int

    @property
    def remaining_count(self) -> int:
        return self.total_count - self.answered_count


@dataclass(frozen=True, slots=True)
class AnswerOutcome:
    is_correct: bool
    confidence: AnswerConfidence
    correct_answer: str
    explanation: str


@dataclass(frozen=True, slots=True)
class AnswerRecord:
    kind: QuestionKind
    is_correct: bool
    confidence: AnswerConfidence

    @property
    def is_sure_and_correct(self) -> bool:
        return self.is_correct and self.confidence is AnswerConfidence.SURE


@dataclass(frozen=True, slots=True)
class CompetencyResult:
    competency_id: int
    competency_name: str
    correct_count: int
    guessed_count: int
    answered_count: int
    assessed: Mastery
    previous: Mastery | None

    @property
    def is_solid(self) -> bool:
        return self.assessed.rank >= DIAGNOSTIC_CEILING.rank


@dataclass(frozen=True, slots=True)
class DiagnosticReport:
    run_id: int
    finished_at: datetime
    results: tuple[CompetencyResult, ...]


def normalize_answer(text: str) -> str:
    return "".join(text.split()).casefold()


def is_correct_answer(question: Question, answer: str) -> bool:
    normalized = normalize_answer(answer)
    return bool(normalized) and any(
        normalized == normalize_answer(accepted) for accepted in question.accepted_answers
    )


def assess_competency(answers: Sequence[AnswerRecord]) -> Mastery:
    if not answers:
        return Mastery.NOT_STUDIED

    sure_correct_share = sum(answer.is_sure_and_correct for answer in answers) / len(answers)
    knows_most = sure_correct_share >= MIN_SURE_CORRECT_SHARE
    application = [answer for answer in answers if answer.kind.proves_application]
    applies_every_time = bool(application) and all(
        answer.is_sure_and_correct for answer in application
    )

    if knows_most and applies_every_time:
        return Mastery.CAN_APPLY
    if knows_most:
        return Mastery.RECOGNIZES
    if any(answer.is_correct for answer in answers):
        return Mastery.BEGINNING
    return Mastery.UNKNOWN


def _active_question_count(conn: sqlite3.Connection) -> int:
    return conn.execute("SELECT COUNT(*) FROM diagnostic_questions WHERE retired = 0").fetchone()[0]


def _row_to_run(conn: sqlite3.Connection, row: sqlite3.Row) -> DiagnosticRun:
    answered = conn.execute(
        "SELECT COUNT(*) FROM diagnostic_answers "
        "JOIN diagnostic_questions ON diagnostic_questions.id = diagnostic_answers.question_id "
        "WHERE diagnostic_answers.run_id = ? AND diagnostic_questions.retired = 0",
        (row["id"],),
    ).fetchone()[0]
    return DiagnosticRun(
        id=row["id"],
        started_at=parse_iso_utc(row["started_at"]),
        finished_at=parse_iso_utc(row["finished_at"]) if row["finished_at"] else None,
        answered_count=answered,
        total_count=_active_question_count(conn),
    )


def find_open_run(conn: sqlite3.Connection, user_id: int) -> DiagnosticRun | None:
    row = conn.execute(
        "SELECT id, started_at, finished_at FROM diagnostic_runs "
        "WHERE user_id = ? AND finished_at IS NULL",
        (user_id,),
    ).fetchone()
    return _row_to_run(conn, row) if row is not None else None


def start_or_resume_run(
    conn: sqlite3.Connection, user_id: int, now: datetime
) -> tuple[DiagnosticRun, bool]:
    if _active_question_count(conn) == 0:
        raise NoQuestionsError()

    existing = find_open_run(conn, user_id)
    if existing is not None:
        return existing, True

    with conn:
        conn.execute(
            "INSERT INTO diagnostic_runs (user_id, started_at) VALUES (?, ?)",
            (user_id, to_iso_utc(now)),
        )
    started = find_open_run(conn, user_id)
    assert started is not None
    return started, False


_QUESTION_COLUMNS = (
    "diagnostic_questions.id, diagnostic_questions.slug, diagnostic_questions.competency_id, "
    "competencies.name AS competency_name, diagnostic_questions.kind, diagnostic_questions.prompt, "
    "diagnostic_questions.options, diagnostic_questions.accepted_answers, "
    "diagnostic_questions.explanation"
)


def _row_to_question(row: sqlite3.Row) -> Question:
    return Question(
        id=row["id"],
        slug=row["slug"],
        competency_id=row["competency_id"],
        competency_name=row["competency_name"],
        kind=QuestionKind(row["kind"]),
        prompt=row["prompt"],
        options=tuple(json.loads(row["options"])),
        accepted_answers=tuple(json.loads(row["accepted_answers"])),
        explanation=row["explanation"],
    )


def next_question(conn: sqlite3.Connection, run_id: int) -> Question | None:
    row = conn.execute(
        f"SELECT {_QUESTION_COLUMNS} FROM diagnostic_questions "
        "JOIN competencies ON competencies.id = diagnostic_questions.competency_id "
        "WHERE diagnostic_questions.retired = 0 AND diagnostic_questions.id NOT IN "
        "(SELECT question_id FROM diagnostic_answers WHERE run_id = ?) "
        "ORDER BY competencies.id, diagnostic_questions.position LIMIT 1",
        (run_id,),
    ).fetchone()
    return _row_to_question(row) if row is not None else None


def record_answer(
    conn: sqlite3.Connection,
    run_id: int,
    question: Question,
    answer: str,
    confidence: AnswerConfidence,
    duration_seconds: int | None,
    now: datetime,
) -> AnswerOutcome:
    if confidence is AnswerConfidence.DONT_KNOW:
        answer = ""
    is_correct = confidence is not AnswerConfidence.DONT_KNOW and is_correct_answer(
        question, answer
    )
    with conn:
        conn.execute(
            "INSERT INTO diagnostic_answers "
            "(run_id, question_id, answer, is_correct, confidence, duration_seconds, answered_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                run_id,
                question.id,
                answer,
                int(is_correct),
                confidence,
                duration_seconds,
                to_iso_utc(now),
            ),
        )
    return AnswerOutcome(is_correct, confidence, question.correct_answer, question.explanation)


def _answers_by_competency(
    conn: sqlite3.Connection, run_id: int
) -> dict[tuple[int, str], list[AnswerRecord]]:
    grouped: dict[tuple[int, str], list[AnswerRecord]] = defaultdict(list)
    for row in conn.execute(
        "SELECT competencies.id, competencies.name, diagnostic_questions.kind, "
        "diagnostic_answers.is_correct, diagnostic_answers.confidence "
        "FROM diagnostic_answers "
        "JOIN diagnostic_questions ON diagnostic_questions.id = diagnostic_answers.question_id "
        "JOIN competencies ON competencies.id = diagnostic_questions.competency_id "
        "WHERE diagnostic_answers.run_id = ? ORDER BY competencies.id",
        (run_id,),
    ):
        grouped[(row["id"], row["name"])].append(
            AnswerRecord(
                QuestionKind(row["kind"]),
                bool(row["is_correct"]),
                AnswerConfidence(row["confidence"]),
            )
        )
    return grouped


def _previous_masteries(conn: sqlite3.Connection, run_id: int) -> dict[int, Mastery]:
    rows = conn.execute(
        "SELECT competency_id, from_mastery FROM mastery_events WHERE source = ? AND source_id = ?",
        (DIAGNOSTIC_SOURCE, run_id),
    )
    return {row["competency_id"]: Mastery(row["from_mastery"]) for row in rows}


def _build_report(conn: sqlite3.Connection, run_id: int, finished_at: datetime) -> DiagnosticReport:
    previous = _previous_masteries(conn, run_id)
    results = tuple(
        CompetencyResult(
            competency_id=competency_id,
            competency_name=competency_name,
            correct_count=sum(answer.is_correct for answer in answers),
            guessed_count=sum(
                answer.is_correct and answer.confidence is AnswerConfidence.GUESS
                for answer in answers
            ),
            answered_count=len(answers),
            assessed=assess_competency(answers),
            previous=previous.get(competency_id),
        )
        for (competency_id, competency_name), answers in _answers_by_competency(
            conn, run_id
        ).items()
    )
    return DiagnosticReport(run_id, finished_at, results)


def _is_above_diagnostic_reach(mastery: Mastery) -> bool:
    return mastery.rank > DIAGNOSTIC_CEILING.rank


def finish_run(conn: sqlite3.Connection, user_id: int, now: datetime) -> DiagnosticReport:
    run = find_open_run(conn, user_id)
    if run is None:
        raise NoOpenDiagnosticError()
    if run.remaining_count > 0:
        raise DiagnosticIncompleteError(run.remaining_count)

    with conn:
        for (competency_id, _), answers in _answers_by_competency(conn, run.id).items():
            if _is_above_diagnostic_reach(current_mastery(conn, user_id, competency_id)):
                continue
            record_mastery(
                conn,
                user_id,
                competency_id,
                assess_competency(answers),
                DIAGNOSTIC_SOURCE,
                run.id,
                now,
            )
        conn.execute(
            "UPDATE diagnostic_runs SET finished_at = ? WHERE id = ?", (to_iso_utc(now), run.id)
        )
    return _build_report(conn, run.id, now)


def _latest_finished_run(conn: sqlite3.Connection, user_id: int) -> sqlite3.Row | None:
    return conn.execute(
        "SELECT id, finished_at FROM diagnostic_runs "
        "WHERE user_id = ? AND finished_at IS NOT NULL ORDER BY finished_at DESC, id DESC LIMIT 1",
        (user_id,),
    ).fetchone()


def last_finished_at(conn: sqlite3.Connection, user_id: int) -> datetime | None:
    row = _latest_finished_run(conn, user_id)
    return parse_iso_utc(row["finished_at"]) if row is not None else None


def latest_report(conn: sqlite3.Connection, user_id: int) -> DiagnosticReport:
    row = _latest_finished_run(conn, user_id)
    if row is None:
        raise NoFinishedDiagnosticError()
    return _build_report(conn, row["id"], parse_iso_utc(row["finished_at"]))
