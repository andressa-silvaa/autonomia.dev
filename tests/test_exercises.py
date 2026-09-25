from __future__ import annotations

import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from hone.core.models import AnswerFormat, ExerciseStatus, GradingMethod, Mastery
from hone.engines.exercises import (
    NoHintsLeftError,
    current_draft,
    evidence_for,
    promotion_target,
    record_attempt,
    resolve_exercise,
    reveal_hint,
    save_draft,
    start_exercise,
)
from hone.engines.mastery import current_mastery, record_mastery
from hone.engines.metrics import build_practice_stats
from hone.engines.progress import (
    ModuleLockedError,
    RequiredExercisesPendingError,
    complete_module,
    resolve_module,
)
from hone.engines.xp import activity_xp, competency_xp, xp_totals

NOW = datetime(2026, 9, 25, 12, 0, tzinfo=UTC)


def _exercise(conn: sqlite3.Connection, user_id: int, slug: str):
    return resolve_exercise(conn, user_id, slug)


def _start(conn, user_id, slug, exercises_dir: Path, workspace_dir: Path):
    exercise = _exercise(conn, user_id, slug)
    module = resolve_module(conn, user_id, exercise.module_key)
    return start_exercise(conn, user_id, exercise, module, exercises_dir, workspace_dir, NOW)


def _attempt(conn, user_id, slug, passed, graded_by=GradingMethod.AUTOMATED_TESTS, at=NOW):
    exercise = _exercise(conn, user_id, slug)
    return record_attempt(
        conn, user_id, exercise, "answer", float(passed), passed, "", graded_by, False, at
    )


def _competency_id(conn: sqlite3.Connection, slug: str) -> int:
    return conn.execute("SELECT id FROM competencies WHERE slug = ?", (slug,)).fetchone()[0]


@pytest.mark.parametrize(
    ("answer_format", "graded_by", "hints", "expected"),
    [
        (AnswerFormat.CODE, GradingMethod.AUTOMATED_TESTS, 0, 20),
        (AnswerFormat.CHOICE, GradingMethod.AUTOMATED_TESTS, 0, 10),
        (AnswerFormat.TEXT, GradingMethod.SELF_ASSESSMENT, 0, 10),
        (AnswerFormat.CODE, GradingMethod.AUTOMATED_TESTS, 2, 10),
        (AnswerFormat.CODE, GradingMethod.AUTOMATED_TESTS, 9, 5),
    ],
)
def test_competency_xp_rules(answer_format, graded_by, hints, expected) -> None:
    assert competency_xp(20, answer_format, graded_by, hints) == expected


def test_activity_xp_stops_after_a_few_attempts() -> None:
    assert [activity_xp(previous) for previous in range(5)] == [2, 2, 2, 0, 0]


@pytest.mark.parametrize(
    ("current", "evidence", "expected"),
    [
        (Mastery.NOT_STUDIED, Mastery.CAN_APPLY, Mastery.CAN_APPLY),
        (Mastery.CAN_APPLY, Mastery.RECOGNIZES, None),
        (Mastery.BEGINNING, Mastery.CAN_EXPLAIN, Mastery.RECOGNIZES),
        (Mastery.RECOGNIZES, Mastery.CAN_EXPLAIN, None),
        (Mastery.CAN_APPLY, Mastery.CAN_EXPLAIN, Mastery.CAN_EXPLAIN),
    ],
)
def test_promotion_only_goes_up_and_explaining_needs_applying(current, evidence, expected) -> None:
    assert promotion_target(current, evidence) is expected


def test_start_creates_workspace_without_overwriting(
    synced_with_exercises: sqlite3.Connection,
    user_id: int,
    exercises_dir: Path,
    workspace_dir: Path,
) -> None:
    conn = synced_with_exercises
    folder = _start(conn, user_id, "double-it", exercises_dir, workspace_dir)
    assert folder is not None
    solution = folder / "solution.py"
    assert "raise NotImplementedError" in solution.read_text(encoding="utf-8")
    assert "Implemente" in (folder / "README.md").read_text(encoding="utf-8")

    solution.write_text("mine", encoding="utf-8")
    _start(conn, user_id, "double-it", exercises_dir, workspace_dir)
    assert solution.read_text(encoding="utf-8") == "mine"
    assert _exercise(conn, user_id, "double-it").status is ExerciseStatus.STARTED
    assert resolve_module(conn, user_id, "first").status.value == "in_progress"


def test_drafts_fall_back_to_the_starter_until_saved(
    synced_with_exercises: sqlite3.Connection,
    user_id: int,
    exercises_dir: Path,
    workspace_dir: Path,
) -> None:
    conn = synced_with_exercises
    exercise = _exercise(conn, user_id, "double-it")
    assert "raise NotImplementedError" in current_draft(exercises_dir, workspace_dir, exercise)
    module = resolve_module(conn, user_id, "first")
    save_draft(conn, user_id, exercise, module, exercises_dir, workspace_dir, "draft", NOW)
    assert current_draft(exercises_dir, workspace_dir, exercise) == "draft"


def test_exercises_of_locked_modules_cannot_start(
    synced_with_exercises: sqlite3.Connection,
    user_id: int,
    exercises_dir: Path,
    workspace_dir: Path,
) -> None:
    with pytest.raises(ModuleLockedError):
        _start(synced_with_exercises, user_id, "self-check", exercises_dir, workspace_dir)


def test_hints_are_revealed_in_order_until_they_run_out(
    synced_with_exercises: sqlite3.Connection, user_id: int
) -> None:
    conn = synced_with_exercises
    assert (
        reveal_hint(conn, user_id, _exercise(conn, user_id, "pick-right"), NOW) == "primeira dica"
    )
    assert reveal_hint(conn, user_id, _exercise(conn, user_id, "pick-right"), NOW) == "segunda dica"
    with pytest.raises(NoHintsLeftError):
        reveal_hint(conn, user_id, _exercise(conn, user_id, "pick-right"), NOW)


def test_first_pass_grants_xp_once_and_hints_cost_xp(
    synced_with_exercises: sqlite3.Connection, user_id: int
) -> None:
    conn = synced_with_exercises
    reveal_hint(conn, user_id, _exercise(conn, user_id, "pick-right"), NOW)

    failed = _attempt(conn, user_id, "pick-right", False)
    assert (failed.passed, failed.competency_xp, failed.activity_xp) == (False, 0, 2)
    passed = _attempt(conn, user_id, "pick-right", True, at=NOW + timedelta(minutes=5))
    assert (passed.first_pass, passed.competency_xp) == (True, 4)
    again = _attempt(conn, user_id, "pick-right", True, at=NOW + timedelta(minutes=6))
    assert (again.first_pass, again.competency_xp, again.activity_xp) == (False, 0, 2)
    fourth = _attempt(conn, user_id, "pick-right", True, at=NOW + timedelta(minutes=7))
    assert fourth.activity_xp == 0

    totals = xp_totals(conn, user_id)
    assert (totals.competency, totals.activity) == (4, 6)


def test_passing_promotes_the_module_competencies(
    synced_with_exercises: sqlite3.Connection, user_id: int
) -> None:
    conn = synced_with_exercises
    choice = _attempt(conn, user_id, "pick-right", True)
    assert [(p.before, p.after) for p in choice.promotions] == [
        (Mastery.NOT_STUDIED, Mastery.RECOGNIZES)
    ]
    code = _attempt(conn, user_id, "double-it", True)
    assert [p.after for p in code.promotions] == [Mastery.CAN_APPLY]
    assert current_mastery(conn, user_id, _competency_id(conn, "basics")) is Mastery.CAN_APPLY


def test_explanations_reach_can_explain_only_with_ollama(
    synced_with_exercises: sqlite3.Connection, user_id: int
) -> None:
    conn = synced_with_exercises
    explain = _exercise(conn, user_id, "explain-it")
    assert evidence_for(explain, GradingMethod.LOCAL_AI) is Mastery.CAN_EXPLAIN
    assert evidence_for(explain, GradingMethod.SELF_ASSESSMENT) is Mastery.RECOGNIZES

    advanced = _competency_id(conn, "advanced")
    with conn:
        record_mastery(conn, user_id, advanced, Mastery.CAN_APPLY, "test", None, NOW)
    outcome = _attempt(conn, user_id, "explain-it", True, GradingMethod.LOCAL_AI)
    assert [p.after for p in outcome.promotions] == [Mastery.CAN_EXPLAIN]


def test_required_exercises_lock_module_completion(
    synced_with_exercises: sqlite3.Connection, user_id: int
) -> None:
    conn = synced_with_exercises
    with pytest.raises(RequiredExercisesPendingError) as caught:
        complete_module(conn, user_id, resolve_module(conn, user_id, "first"), NOW)
    assert caught.value.pending_titles == ["Escolha a certa"]

    outcome = _attempt(conn, user_id, "pick-right", True)
    assert outcome.pending_required == ()
    unlocked = complete_module(conn, user_id, resolve_module(conn, user_id, "first"), NOW)
    assert [module.slug for module in unlocked] == ["second"]


def test_practice_stats_per_competency(
    synced_with_exercises: sqlite3.Connection, user_id: int
) -> None:
    conn = synced_with_exercises
    _attempt(conn, user_id, "pick-right", True)
    _attempt(conn, user_id, "double-it", False)
    _attempt(conn, user_id, "double-it", True, at=NOW + timedelta(minutes=1))

    stats = build_practice_stats(conn, user_id)
    basics = next(item for item in stats.competencies if item.name == "Básico")
    assert (basics.exercises_total, basics.exercises_passed, basics.attempts) == (2, 2, 3)
    assert basics.first_try_passes == 1
    assert basics.first_try_rate == 0.5
    assert stats.exercises_passed == 2
    assert stats.xp.competency == 5 + 10
