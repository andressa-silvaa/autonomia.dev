from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from hone.core.clock import parse_iso_utc, to_iso_utc
from hone.core.models import (
    AnswerFormat,
    ExerciseKind,
    ExerciseStatus,
    GradingMethod,
    Mastery,
    XpKind,
)
from hone.engines.exercise_bank import STARTER_FILENAME, STATEMENT_FILENAME, TESTS_FILENAME
from hone.engines.mastery import current_mastery, record_mastery
from hone.engines.progress import (
    ModuleLockedError,
    ModuleView,
    pending_required_exercises,
    start_module,
)
from hone.engines.sessions import find_active_session
from hone.engines.xp import activity_xp, competency_xp, grant_xp

EXERCISE_SOURCE = "exercise"
SOLUTION_FILENAME = "solution.py"
ANSWER_FILENAME = "answer.md"
ANSWER_TEMPLATE = "# Sua resposta\n\n"


class UnknownExerciseError(Exception):
    def __init__(self, reference: str) -> None:
        super().__init__(f"Unknown exercise: {reference!r}")
        self.reference = reference


class ExerciseNotStartedError(Exception):
    def __init__(self, exercise: Exercise) -> None:
        super().__init__(f"Exercise {exercise.slug!r} has no workspace yet")
        self.exercise = exercise


class EmptyAnswerError(Exception):
    def __init__(self, exercise: Exercise, answer_path: Path) -> None:
        super().__init__(f"Answer for {exercise.slug!r} is empty")
        self.exercise = exercise
        self.answer_path = answer_path


class NoHintsLeftError(Exception):
    def __init__(self, exercise: Exercise) -> None:
        super().__init__(f"Exercise {exercise.slug!r} has no more hints")
        self.exercise = exercise


@dataclass(frozen=True, slots=True)
class Exercise:
    id: int
    slug: str
    title: str
    kind: ExerciseKind
    grading: GradingMethod
    statement: str
    difficulty: int
    base_xp: int
    required: bool
    options: tuple[str, ...]
    accepted_answers: tuple[str, ...]
    rubric: tuple[str, ...]
    hints: tuple[str, ...]
    reference_answer: str
    source_path: str
    module_id: int
    module_key: str
    module_title: str
    status: ExerciseStatus
    attempts_count: int
    hints_revealed: int
    started_at: datetime | None

    @property
    def answer_format(self) -> AnswerFormat:
        if self.options:
            return AnswerFormat.CHOICE
        if self.accepted_answers:
            return AnswerFormat.TYPED
        if self.rubric:
            return AnswerFormat.TEXT
        return AnswerFormat.CODE

    @property
    def needs_workspace(self) -> bool:
        return self.answer_format in (AnswerFormat.CODE, AnswerFormat.TEXT)

    @property
    def is_passed(self) -> bool:
        return self.status is ExerciseStatus.PASSED

    @property
    def hints_left(self) -> int:
        return len(self.hints) - self.hints_revealed


@dataclass(frozen=True, slots=True)
class AttemptRecord:
    submitted_at: datetime
    score: float | None
    passed: bool
    graded_by: str
    hints_used: int
    used_ai: bool
    duration_seconds: int | None
    feedback: str


@dataclass(frozen=True, slots=True)
class MasteryPromotion:
    competency_name: str
    before: Mastery
    after: Mastery


@dataclass(frozen=True, slots=True)
class AttemptOutcome:
    attempt_id: int
    passed: bool
    first_pass: bool
    competency_xp: int
    activity_xp: int
    promotions: tuple[MasteryPromotion, ...]
    pending_required: tuple[str, ...]


_EXERCISE_QUERY = (
    "SELECT exercises.id, exercises.slug, exercises.title, exercises.kind, exercises.grading, "
    "exercises.prompt, exercises.difficulty, exercises.xp, exercises.required, "
    "exercises.options, exercises.accepted_answers, exercises.rubric, exercises.hints, "
    "exercises.reference_answer, exercises.source_path, exercises.module_id, "
    "tracks.slug AS track_slug, modules.slug AS module_slug, modules.title AS module_title, "
    "exercise_progress.started_at, exercise_progress.passed_at, "
    "COALESCE(exercise_progress.hints_revealed, 0) AS hints_revealed, "
    "(SELECT COUNT(*) FROM attempts WHERE attempts.exercise_id = exercises.id "
    " AND attempts.user_id = ?) AS attempts_count "
    "FROM exercises "
    "JOIN modules ON modules.id = exercises.module_id "
    "JOIN tracks ON tracks.id = modules.track_id "
    "LEFT JOIN exercise_progress ON exercise_progress.exercise_id = exercises.id "
    "AND exercise_progress.user_id = ? "
    "WHERE exercises.retired = 0 "
)


def _status_of(row: sqlite3.Row) -> ExerciseStatus:
    if row["passed_at"] is not None:
        return ExerciseStatus.PASSED
    if row["started_at"] is not None:
        return ExerciseStatus.STARTED
    return ExerciseStatus.NOT_STARTED


def _row_to_exercise(row: sqlite3.Row) -> Exercise:
    return Exercise(
        id=row["id"],
        slug=row["slug"],
        title=row["title"],
        kind=ExerciseKind(row["kind"]),
        grading=GradingMethod(row["grading"]),
        statement=row["prompt"],
        difficulty=row["difficulty"],
        base_xp=row["xp"],
        required=bool(row["required"]),
        options=tuple(json.loads(row["options"])),
        accepted_answers=tuple(json.loads(row["accepted_answers"])),
        rubric=tuple(json.loads(row["rubric"])),
        hints=tuple(json.loads(row["hints"])),
        reference_answer=row["reference_answer"],
        source_path=row["source_path"],
        module_id=row["module_id"],
        module_key=f"{row['track_slug']}/{row['module_slug']}",
        module_title=row["module_title"],
        status=_status_of(row),
        attempts_count=row["attempts_count"],
        hints_revealed=row["hints_revealed"],
        started_at=parse_iso_utc(row["started_at"]) if row["started_at"] else None,
    )


def list_exercises(
    conn: sqlite3.Connection, user_id: int, module_id: int | None = None
) -> list[Exercise]:
    module_filter = "AND exercises.module_id = ? " if module_id is not None else ""
    parameters = (user_id, user_id) + ((module_id,) if module_id is not None else ())
    rows = conn.execute(
        _EXERCISE_QUERY + module_filter + "ORDER BY tracks.name, modules.position, "
        "exercises.position",
        parameters,
    )
    return [_row_to_exercise(row) for row in rows]


def resolve_exercise(conn: sqlite3.Connection, user_id: int, reference: str) -> Exercise:
    slug = reference.strip().split("/")[-1]
    row = conn.execute(_EXERCISE_QUERY + "AND exercises.slug = ?", (user_id, user_id, slug))
    found = row.fetchone()
    if found is None:
        raise UnknownExerciseError(reference)
    return _row_to_exercise(found)


def workspace_path(workspace_dir: Path, exercise: Exercise) -> Path:
    return workspace_dir / exercise.source_path


def answer_path(workspace_dir: Path, exercise: Exercise) -> Path:
    filename = SOLUTION_FILENAME if exercise.answer_format is AnswerFormat.CODE else ANSWER_FILENAME
    return workspace_path(workspace_dir, exercise) / filename


def tests_path(exercises_dir: Path, exercise: Exercise) -> Path:
    return exercises_dir / exercise.source_path / TESTS_FILENAME


def _write_if_missing(path: Path, content: str) -> None:
    if not path.exists():
        path.write_text(content, encoding="utf-8")


def _prepare_workspace(exercises_dir: Path, workspace_dir: Path, exercise: Exercise) -> Path:
    folder = workspace_path(workspace_dir, exercise)
    folder.mkdir(parents=True, exist_ok=True)
    _write_if_missing(folder / STATEMENT_FILENAME, f"# {exercise.title}\n\n{exercise.statement}\n")
    if exercise.answer_format is AnswerFormat.CODE:
        starter = exercises_dir / exercise.source_path / STARTER_FILENAME
        _write_if_missing(folder / SOLUTION_FILENAME, starter.read_text(encoding="utf-8"))
    elif exercise.answer_format is AnswerFormat.TEXT:
        _write_if_missing(folder / ANSWER_FILENAME, ANSWER_TEMPLATE)
    return folder


def _ensure_progress(
    conn: sqlite3.Connection, user_id: int, exercise_id: int, now: datetime
) -> None:
    conn.execute(
        "INSERT INTO exercise_progress (user_id, exercise_id, started_at) VALUES (?, ?, ?) "
        "ON CONFLICT (user_id, exercise_id) DO NOTHING",
        (user_id, exercise_id, to_iso_utc(now)),
    )


def start_exercise(
    conn: sqlite3.Connection,
    user_id: int,
    exercise: Exercise,
    module: ModuleView,
    exercises_dir: Path,
    workspace_dir: Path,
    now: datetime,
) -> Path | None:
    if not module.is_open:
        raise ModuleLockedError(module)
    start_module(conn, user_id, module, now)
    folder = (
        _prepare_workspace(exercises_dir, workspace_dir, exercise)
        if exercise.needs_workspace
        else None
    )
    with conn:
        _ensure_progress(conn, user_id, exercise.id, now)
    return folder


def current_draft(exercises_dir: Path, workspace_dir: Path, exercise: Exercise) -> str:
    saved = answer_path(workspace_dir, exercise)
    if saved.is_file():
        return saved.read_text(encoding="utf-8")
    if exercise.answer_format is AnswerFormat.CODE:
        return (exercises_dir / exercise.source_path / STARTER_FILENAME).read_text(encoding="utf-8")
    if exercise.answer_format is AnswerFormat.TEXT:
        return ANSWER_TEMPLATE
    return ""


def save_draft(
    conn: sqlite3.Connection,
    user_id: int,
    exercise: Exercise,
    module: ModuleView,
    exercises_dir: Path,
    workspace_dir: Path,
    content: str,
    now: datetime,
) -> Path:
    start_exercise(conn, user_id, exercise, module, exercises_dir, workspace_dir, now)
    path = answer_path(workspace_dir, exercise)
    path.write_text(content, encoding="utf-8", newline="\n")
    return path


def reveal_hint(conn: sqlite3.Connection, user_id: int, exercise: Exercise, now: datetime) -> str:
    if exercise.hints_left <= 0:
        raise NoHintsLeftError(exercise)
    with conn:
        _ensure_progress(conn, user_id, exercise.id, now)
        conn.execute(
            "UPDATE exercise_progress SET hints_revealed = hints_revealed + 1 "
            "WHERE user_id = ? AND exercise_id = ?",
            (user_id, exercise.id),
        )
    return exercise.hints[exercise.hints_revealed]


def read_written_answer(workspace_dir: Path, exercise: Exercise) -> str:
    path = answer_path(workspace_dir, exercise)
    if not path.is_file():
        raise ExerciseNotStartedError(exercise)
    text = path.read_text(encoding="utf-8")
    meaningful = text.replace(ANSWER_TEMPLATE.strip(), "").strip()
    if not meaningful:
        raise EmptyAnswerError(exercise, path)
    return text


def evidence_for(exercise: Exercise, graded_by: GradingMethod) -> Mastery:
    if exercise.answer_format is AnswerFormat.CODE:
        return Mastery.CAN_APPLY
    if exercise.answer_format is AnswerFormat.TEXT and graded_by is GradingMethod.LOCAL_AI:
        return Mastery.CAN_EXPLAIN
    return Mastery.RECOGNIZES


def promotion_target(current: Mastery, evidence: Mastery) -> Mastery | None:
    if evidence.rank > Mastery.CAN_APPLY.rank and current.rank < Mastery.CAN_APPLY.rank:
        evidence = Mastery.RECOGNIZES
    return evidence if evidence.rank > current.rank else None


def _module_competencies(conn: sqlite3.Connection, module_id: int) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT competencies.id, competencies.name FROM module_competencies "
        "JOIN competencies ON competencies.id = module_competencies.competency_id "
        "WHERE module_competencies.module_id = ? ORDER BY competencies.id",
        (module_id,),
    ).fetchall()


def _promote_competencies(
    conn: sqlite3.Connection,
    user_id: int,
    exercise: Exercise,
    evidence: Mastery,
    attempt_id: int,
    now: datetime,
) -> tuple[MasteryPromotion, ...]:
    promotions = []
    for competency in _module_competencies(conn, exercise.module_id):
        before = current_mastery(conn, user_id, competency["id"])
        target = promotion_target(before, evidence)
        if target is None:
            continue
        record_mastery(conn, user_id, competency["id"], target, EXERCISE_SOURCE, attempt_id, now)
        promotions.append(MasteryPromotion(competency["name"], before, target))
    return tuple(promotions)


def _elapsed_seconds(exercise: Exercise, now: datetime) -> int | None:
    if exercise.started_at is None:
        return None
    return max(0, int((now - exercise.started_at).total_seconds()))


def record_attempt(
    conn: sqlite3.Connection,
    user_id: int,
    exercise: Exercise,
    answer: str,
    score: float,
    passed: bool,
    feedback: str,
    graded_by: GradingMethod,
    used_ai: bool,
    now: datetime,
) -> AttemptOutcome:
    session = find_active_session(conn, user_id)
    first_pass = passed and not exercise.is_passed
    with conn:
        _ensure_progress(conn, user_id, exercise.id, now)
        cursor = conn.execute(
            "INSERT INTO attempts (user_id, exercise_id, session_id, submitted_at, answer, score, "
            "feedback, duration_seconds, hints_used, used_ai, passed, graded_by) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                user_id,
                exercise.id,
                session.id if session else None,
                to_iso_utc(now),
                answer,
                score,
                feedback,
                _elapsed_seconds(exercise, now),
                exercise.hints_revealed,
                int(used_ai),
                int(passed),
                graded_by,
            ),
        )
        attempt_id = cursor.lastrowid
        assert attempt_id is not None

        effort_xp = activity_xp(exercise.attempts_count)
        grant_xp(conn, user_id, XpKind.ACTIVITY, effort_xp, attempt_id, now)

        earned_xp = 0
        promotions: tuple[MasteryPromotion, ...] = ()
        if first_pass:
            conn.execute(
                "UPDATE exercise_progress SET passed_at = ? WHERE user_id = ? AND exercise_id = ?",
                (to_iso_utc(now), user_id, exercise.id),
            )
            earned_xp = competency_xp(
                exercise.base_xp, exercise.answer_format, graded_by, exercise.hints_revealed
            )
            grant_xp(conn, user_id, XpKind.COMPETENCY, earned_xp, attempt_id, now)
            promotions = _promote_competencies(
                conn, user_id, exercise, evidence_for(exercise, graded_by), attempt_id, now
            )

    return AttemptOutcome(
        attempt_id=attempt_id,
        passed=passed,
        first_pass=first_pass,
        competency_xp=earned_xp,
        activity_xp=effort_xp,
        promotions=promotions,
        pending_required=tuple(pending_required_exercises(conn, user_id, exercise.module_id)),
    )


def list_attempts(conn: sqlite3.Connection, user_id: int, exercise_id: int) -> list[AttemptRecord]:
    rows = conn.execute(
        "SELECT submitted_at, score, passed, graded_by, hints_used, used_ai, duration_seconds, "
        "feedback FROM attempts WHERE user_id = ? AND exercise_id = ? ORDER BY submitted_at, id",
        (user_id, exercise_id),
    )
    return [
        AttemptRecord(
            submitted_at=parse_iso_utc(row["submitted_at"]),
            score=row["score"],
            passed=bool(row["passed"]),
            graded_by=row["graded_by"],
            hints_used=row["hints_used"],
            used_ai=bool(row["used_ai"]),
            duration_seconds=row["duration_seconds"],
            feedback=row["feedback"],
        )
        for row in rows
    ]
