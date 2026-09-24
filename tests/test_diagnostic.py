from __future__ import annotations

import sqlite3
from datetime import UTC, datetime, timedelta

import pytest

from hone.core.models import AnswerConfidence, Mastery, QuestionKind
from hone.engines.diagnostic import (
    AnswerRecord,
    DiagnosticIncompleteError,
    NoFinishedDiagnosticError,
    NoOpenDiagnosticError,
    NoQuestionsError,
    Question,
    assess_competency,
    finish_run,
    is_correct_answer,
    last_finished_at,
    latest_report,
    next_question,
    record_answer,
    start_or_resume_run,
)
from hone.engines.mastery import current_mastery, record_mastery

NOW = datetime(2026, 9, 24, 12, 0, tzinfo=UTC)
SURE = AnswerConfidence.SURE
GUESS = AnswerConfidence.GUESS
DONT_KNOW = AnswerConfidence.DONT_KNOW
CONCEPT = QuestionKind.CONCEPT
CODE = QuestionKind.CODE_READING


def _question(accepted: tuple[str, ...]) -> Question:
    return Question(1, "q", 1, "C", CODE, "?", (), accepted, "")


def _competency_id(conn: sqlite3.Connection, slug: str) -> int:
    return conn.execute("SELECT id FROM competencies WHERE slug = ?", (slug,)).fetchone()[0]


def _answer_all(conn: sqlite3.Connection, run_id: int, answers: dict[str, tuple[str, str]]) -> None:
    confidences = {"sure": SURE, "guess": GUESS, "dont_know": DONT_KNOW}
    while (question := next_question(conn, run_id)) is not None:
        answer, confidence = answers[question.slug]
        record_answer(conn, run_id, question, answer, confidences[confidence], 5, NOW)


def test_typed_answers_ignore_spacing_and_case() -> None:
    question = _question(("contagem.get(p, 0)",))
    assert is_correct_answer(question, "contagem.get(p,0)")
    assert is_correct_answer(question, "  CONTAGEM.GET(P, 0) ")
    assert not is_correct_answer(question, "contagem[p]")
    assert not is_correct_answer(question, "   ")


@pytest.mark.parametrize(
    ("answers", "expected"),
    [
        ([], Mastery.NOT_STUDIED),
        ([(CONCEPT, False, DONT_KNOW), (CODE, False, SURE)], Mastery.UNKNOWN),
        ([(CONCEPT, True, GUESS), (CODE, False, SURE)], Mastery.BEGINNING),
        ([(CONCEPT, True, SURE), (CODE, False, SURE)], Mastery.RECOGNIZES),
        ([(CONCEPT, True, SURE), (CONCEPT, True, SURE)], Mastery.RECOGNIZES),
        ([(CONCEPT, True, SURE), (CODE, True, GUESS)], Mastery.RECOGNIZES),
        ([(CONCEPT, False, SURE), (CODE, True, SURE)], Mastery.CAN_APPLY),
        ([(CONCEPT, True, SURE), (CODE, True, SURE), (CODE, True, SURE)], Mastery.CAN_APPLY),
    ],
)
def test_assessment_rules(
    answers: list[tuple[QuestionKind, bool, AnswerConfidence]], expected: Mastery
) -> None:
    records = [AnswerRecord(kind, correct, confidence) for kind, correct, confidence in answers]
    assert assess_competency(records) is expected


def test_start_without_questions_is_a_challenge(conn: sqlite3.Connection, user_id: int) -> None:
    with pytest.raises(NoQuestionsError):
        start_or_resume_run(conn, user_id, NOW)


def test_questions_come_in_competency_order_and_run_resumes(
    synced: sqlite3.Connection, user_id: int
) -> None:
    run, resumed = start_or_resume_run(synced, user_id, NOW)
    assert (resumed, run.answered_count, run.total_count) == (False, 0, 3)

    first = next_question(synced, run.id)
    assert first is not None and first.slug == "basics-concept"
    outcome = record_answer(synced, run.id, first, "certa", SURE, 12, NOW)
    assert outcome.is_correct and outcome.explanation == "Porque sim."

    again, resumed = start_or_resume_run(synced, user_id, NOW + timedelta(hours=1))
    assert (resumed, again.id, again.answered_count) == (True, run.id, 1)
    second = next_question(synced, run.id)
    assert second is not None and second.slug == "basics-code"


def test_dont_know_is_stored_as_wrong_even_with_a_right_answer(
    synced: sqlite3.Connection, user_id: int
) -> None:
    run, _ = start_or_resume_run(synced, user_id, NOW)
    question = next_question(synced, run.id)
    assert question is not None
    outcome = record_answer(synced, run.id, question, "certa", DONT_KNOW, None, NOW)
    assert not outcome.is_correct
    assert outcome.correct_answer == "certa"
    row = synced.execute("SELECT answer, confidence FROM diagnostic_answers").fetchone()
    assert (row["answer"], row["confidence"]) == ("", "dont_know")


def test_finish_requires_every_question(synced: sqlite3.Connection, user_id: int) -> None:
    with pytest.raises(NoOpenDiagnosticError):
        finish_run(synced, user_id, NOW)
    start_or_resume_run(synced, user_id, NOW)
    with pytest.raises(DiagnosticIncompleteError) as caught:
        finish_run(synced, user_id, NOW)
    assert caught.value.remaining == 3


def test_finishing_records_mastery_and_history(synced: sqlite3.Connection, user_id: int) -> None:
    run, _ = start_or_resume_run(synced, user_id, NOW)
    _answer_all(
        synced,
        run.id,
        {
            "basics-concept": ("certa", "sure"),
            "basics-code": ("2", "sure"),
            "advanced-concept": ("", "dont_know"),
        },
    )
    report = finish_run(synced, user_id, NOW + timedelta(minutes=10))

    results = {result.competency_name: result for result in report.results}
    assert results["Básico"].assessed is Mastery.CAN_APPLY
    assert results["Básico"].is_solid
    assert (results["Básico"].correct_count, results["Básico"].answered_count) == (2, 2)
    assert results["Básico"].guessed_count == 0
    assert results["Avançado"].assessed is Mastery.UNKNOWN
    assert results["Avançado"].previous is Mastery.NOT_STUDIED

    assert current_mastery(synced, user_id, _competency_id(synced, "basics")) is Mastery.CAN_APPLY
    events = synced.execute(
        "SELECT from_mastery, to_mastery, source FROM mastery_events ORDER BY competency_id"
    ).fetchall()
    assert [tuple(event) for event in events] == [
        ("not_studied", "can_apply", "diagnostic"),
        ("not_studied", "unknown", "diagnostic"),
    ]
    assert latest_report(synced, user_id).results == report.results
    assert last_finished_at(synced, user_id) == NOW + timedelta(minutes=10)


def test_diagnostic_never_overrides_mastery_above_its_reach(
    synced: sqlite3.Connection, user_id: int
) -> None:
    basics = _competency_id(synced, "basics")
    with synced:
        record_mastery(synced, user_id, basics, Mastery.CAN_TEACH, "manual", None, NOW)

    run, _ = start_or_resume_run(synced, user_id, NOW)
    _answer_all(
        synced,
        run.id,
        {
            "basics-concept": ("errada", "sure"),
            "basics-code": ("3", "sure"),
            "advanced-concept": ("não", "guess"),
        },
    )
    finish_run(synced, user_id, NOW)
    assert current_mastery(synced, user_id, basics) is Mastery.CAN_TEACH
    advanced = _competency_id(synced, "advanced")
    assert current_mastery(synced, user_id, advanced) is Mastery.BEGINNING


def test_latest_report_needs_a_finished_run(synced: sqlite3.Connection, user_id: int) -> None:
    with pytest.raises(NoFinishedDiagnosticError):
        latest_report(synced, user_id)
    assert last_finished_at(synced, user_id) is None
