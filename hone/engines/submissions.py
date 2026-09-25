from __future__ import annotations

import sqlite3
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from hone.config import Settings
from hone.core.models import AnswerFormat, GradingMethod
from hone.engines.exercises import (
    AttemptOutcome,
    Exercise,
    answer_path,
    read_written_answer,
    record_attempt,
    save_draft,
    tests_path,
)
from hone.engines.grading import (
    RubricGradingError,
    RubricResult,
    TestRunResult,
    grade_with_ollama,
    matches_accepted_answer,
    run_python_tests,
    self_assessed_result,
)
from hone.engines.ollama import (
    OllamaModelMissingError,
    OllamaResponseError,
    OllamaUnavailableError,
    ensure_model,
)
from hone.engines.progress import ModuleView


class SelfAssessmentReason(StrEnum):
    GRADED_BY_SELF = "graded_by_self"
    OLLAMA_UNAVAILABLE = "ollama_unavailable"
    OLLAMA_MODEL_MISSING = "ollama_model_missing"
    OLLAMA_BAD_RESPONSE = "ollama_bad_response"


class WrongAnswerFormatError(Exception):
    def __init__(self, exercise: Exercise, expected: AnswerFormat) -> None:
        super().__init__(f"Exercise {exercise.slug!r} is not a {expected} exercise")
        self.exercise = exercise


class SelfAssessmentSizeError(Exception):
    def __init__(self, expected: int, received: int) -> None:
        super().__init__(f"Expected {expected} rubric answers, received {received}")


@dataclass(frozen=True, slots=True)
class SubmissionResult:
    outcome: AttemptOutcome | None
    answer_correct: bool | None = None
    test_run: TestRunResult | None = None
    rubric: RubricResult | None = None
    self_assessment_reason: SelfAssessmentReason | None = None

    @property
    def needs_self_assessment(self) -> bool:
        return self.self_assessment_reason is not None


def describe_test_run(result: TestRunResult) -> str:
    if result.timed_out:
        return "tempo esgotado: o código demorou demais (laço infinito ou algoritmo lento?)"
    if result.total == 0:
        return f"os testes nem chegaram a rodar\n{result.output}"
    lines = [f"{result.passed}/{result.total} testes passaram"]
    lines.extend(f"✘ {failure.name}: {failure.message}" for failure in result.failures)
    return "\n".join(lines)


def describe_rubric(result: RubricResult) -> str:
    lines = [
        f"{'✔' if item.met else '✘'} {item.criterion}"
        + (f": {item.comment}" if item.comment else "")
        for item in result.criteria
    ]
    if result.feedback:
        lines.append(result.feedback)
    return "\n".join(lines)


def _require_format(exercise: Exercise, *allowed: AnswerFormat) -> None:
    if exercise.answer_format not in allowed:
        raise WrongAnswerFormatError(exercise, allowed[0])


def submit_answer_key(
    conn: sqlite3.Connection,
    user_id: int,
    exercise: Exercise,
    answer: str,
    used_ai: bool,
    now: datetime,
) -> SubmissionResult:
    _require_format(exercise, AnswerFormat.CHOICE, AnswerFormat.TYPED)
    correct = matches_accepted_answer(answer, exercise.accepted_answers)
    feedback = "resposta certa" if correct else "resposta diferente do gabarito"
    outcome = record_attempt(
        conn,
        user_id,
        exercise,
        answer,
        float(correct),
        correct,
        feedback,
        GradingMethod.AUTOMATED_TESTS,
        used_ai,
        now,
    )
    return SubmissionResult(outcome, answer_correct=correct)


def submit_code(
    conn: sqlite3.Connection,
    settings: Settings,
    user_id: int,
    exercise: Exercise,
    module: ModuleView,
    content: str,
    used_ai: bool,
    now: datetime,
) -> SubmissionResult:
    _require_format(exercise, AnswerFormat.CODE)
    save_draft(
        conn,
        user_id,
        exercise,
        module,
        settings.exercises_dir,
        settings.workspace_dir,
        content,
        now,
    )
    answer = read_written_answer(settings.workspace_dir, exercise)
    result = run_python_tests(
        answer_path(settings.workspace_dir, exercise),
        tests_path(settings.exercises_dir, exercise),
        settings.exercise_timeout_seconds,
    )
    outcome = record_attempt(
        conn,
        user_id,
        exercise,
        answer,
        result.score,
        result.is_passing,
        describe_test_run(result),
        GradingMethod.AUTOMATED_TESTS,
        used_ai,
        now,
    )
    return SubmissionResult(outcome, test_run=result)


def _record_rubric(
    conn: sqlite3.Connection,
    user_id: int,
    exercise: Exercise,
    answer: str,
    rubric: RubricResult,
    used_ai: bool,
    now: datetime,
) -> SubmissionResult:
    outcome = record_attempt(
        conn,
        user_id,
        exercise,
        answer,
        rubric.score,
        rubric.is_passing,
        describe_rubric(rubric),
        rubric.graded_by,
        used_ai,
        now,
    )
    return SubmissionResult(outcome, rubric=rubric)


def _ollama_rubric(settings: Settings, exercise: Exercise, answer: str) -> RubricResult:
    ensure_model(settings.ollama_url, settings.ollama_model)
    return grade_with_ollama(
        settings.ollama_url,
        settings.ollama_model,
        exercise.statement,
        exercise.rubric,
        exercise.reference_answer,
        answer,
    )


def submit_text(
    conn: sqlite3.Connection,
    settings: Settings,
    user_id: int,
    exercise: Exercise,
    module: ModuleView,
    content: str,
    used_ai: bool,
    now: datetime,
) -> SubmissionResult:
    _require_format(exercise, AnswerFormat.TEXT)
    save_draft(
        conn,
        user_id,
        exercise,
        module,
        settings.exercises_dir,
        settings.workspace_dir,
        content,
        now,
    )
    answer = read_written_answer(settings.workspace_dir, exercise)
    if exercise.grading is not GradingMethod.LOCAL_AI:
        return SubmissionResult(None, self_assessment_reason=SelfAssessmentReason.GRADED_BY_SELF)

    try:
        rubric = _ollama_rubric(settings, exercise, answer)
    except OllamaUnavailableError:
        return SubmissionResult(
            None, self_assessment_reason=SelfAssessmentReason.OLLAMA_UNAVAILABLE
        )
    except OllamaModelMissingError:
        return SubmissionResult(
            None, self_assessment_reason=SelfAssessmentReason.OLLAMA_MODEL_MISSING
        )
    except (OllamaResponseError, RubricGradingError):
        return SubmissionResult(
            None, self_assessment_reason=SelfAssessmentReason.OLLAMA_BAD_RESPONSE
        )
    return _record_rubric(conn, user_id, exercise, answer, rubric, used_ai, now)


def submit_self_assessment(
    conn: sqlite3.Connection,
    settings: Settings,
    user_id: int,
    exercise: Exercise,
    met_flags: Sequence[bool],
    used_ai: bool,
    now: datetime,
) -> SubmissionResult:
    _require_format(exercise, AnswerFormat.TEXT)
    if len(met_flags) != len(exercise.rubric):
        raise SelfAssessmentSizeError(len(exercise.rubric), len(met_flags))
    answer = read_written_answer(settings.workspace_dir, exercise)
    rubric = self_assessed_result(exercise.rubric, met_flags)
    return _record_rubric(conn, user_id, exercise, answer, rubric, used_ai, now)
