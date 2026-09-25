from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from hone.api.markdown import render_markdown
from hone.core.models import AnswerFormat, ExerciseKind, ExerciseStatus, GradingMethod, Mastery
from hone.engines.exercises import AttemptRecord, Exercise, MasteryPromotion
from hone.engines.grading import RubricResult, TestRunResult
from hone.engines.metrics import CompetencyPractice, PracticeStats
from hone.engines.submissions import SubmissionResult
from hone.engines.xp import XpTotals
from hone.voice import (
    EXERCISE_KIND_LABELS,
    EXERCISE_STATUS_LABELS,
    GRADING_LABELS,
    exercise_failed_message,
    exercise_passed_message,
    module_ready_message,
    self_assessment_message,
    xp_earned_message,
)


class XpOut(BaseModel):
    competency: int
    activity: int

    @classmethod
    def from_totals(cls, totals: XpTotals) -> XpOut:
        return cls(competency=totals.competency, activity=totals.activity)


class ExerciseSummaryOut(BaseModel):
    slug: str
    title: str
    kind: ExerciseKind
    kind_label: str
    difficulty: int
    base_xp: int
    required: bool
    status: ExerciseStatus
    status_label: str
    answer_format: AnswerFormat

    @classmethod
    def summary_fields(cls, exercise: Exercise) -> dict:
        return {
            "slug": exercise.slug,
            "title": exercise.title,
            "kind": exercise.kind,
            "kind_label": EXERCISE_KIND_LABELS[exercise.kind],
            "difficulty": exercise.difficulty,
            "base_xp": exercise.base_xp,
            "required": exercise.required,
            "status": exercise.status,
            "status_label": EXERCISE_STATUS_LABELS[exercise.status],
            "answer_format": exercise.answer_format,
        }

    @classmethod
    def from_exercise(cls, exercise: Exercise) -> ExerciseSummaryOut:
        return cls(**cls.summary_fields(exercise))


class AttemptOut(BaseModel):
    submitted_at: datetime
    passed: bool
    score: float | None
    graded_by_label: str
    hints_used: int
    used_ai: bool
    duration_seconds: int | None
    feedback: str

    @classmethod
    def from_record(cls, record: AttemptRecord) -> AttemptOut:
        return cls(
            submitted_at=record.submitted_at,
            passed=record.passed,
            score=record.score,
            graded_by_label=GRADING_LABELS.get(record.graded_by, record.graded_by),
            hints_used=record.hints_used,
            used_ai=record.used_ai,
            duration_seconds=record.duration_seconds,
            feedback=record.feedback,
        )


class ExerciseDetailOut(ExerciseSummaryOut):
    module_key: str
    module_title: str
    module_open: bool
    statement_html: str
    options: list[str]
    rubric: list[str]
    grading: GradingMethod
    grading_label: str
    hints_total: int
    hints_revealed: list[str]
    draft: str
    attempts: list[AttemptOut]

    @classmethod
    def from_exercise(
        cls,
        exercise: Exercise,
        module_open: bool,
        draft: str,
        attempts: list[AttemptRecord],
    ) -> ExerciseDetailOut:
        return cls(
            **cls.summary_fields(exercise),
            module_key=exercise.module_key,
            module_title=exercise.module_title,
            module_open=module_open,
            statement_html=render_markdown(exercise.statement),
            options=list(exercise.options),
            rubric=list(exercise.rubric),
            grading=exercise.grading,
            grading_label=GRADING_LABELS[exercise.grading],
            hints_total=len(exercise.hints),
            hints_revealed=list(exercise.hints[: exercise.hints_revealed]),
            draft=draft,
            attempts=[AttemptOut.from_record(record) for record in attempts],
        )


class DraftIn(BaseModel):
    content: str


class SubmissionIn(BaseModel):
    answer: str = ""
    content: str = ""
    used_ai: bool = False


class SelfAssessmentIn(BaseModel):
    met: list[bool]
    used_ai: bool = False


class HintOut(BaseModel):
    hint: str
    number: int
    total: int


class TestFailureOut(BaseModel):
    name: str
    message: str


class TestRunOut(BaseModel):
    passed: int
    total: int
    timed_out: bool
    output: str
    failures: list[TestFailureOut]

    @classmethod
    def from_result(cls, result: TestRunResult) -> TestRunOut:
        return cls(
            passed=result.passed,
            total=result.total,
            timed_out=result.timed_out,
            output=result.output,
            failures=[TestFailureOut(name=f.name, message=f.message) for f in result.failures],
        )


class CriterionOut(BaseModel):
    criterion: str
    met: bool
    comment: str


class RubricOut(BaseModel):
    criteria: list[CriterionOut]
    feedback: str
    graded_by_label: str

    @classmethod
    def from_result(cls, result: RubricResult) -> RubricOut:
        return cls(
            criteria=[
                CriterionOut(criterion=item.criterion, met=item.met, comment=item.comment)
                for item in result.criteria
            ],
            feedback=result.feedback,
            graded_by_label=GRADING_LABELS[result.graded_by],
        )


class PromotionOut(BaseModel):
    competency_name: str
    before: Mastery
    before_label: str
    after: Mastery
    after_label: str

    @classmethod
    def from_promotion(cls, promotion: MasteryPromotion) -> PromotionOut:
        return cls(
            competency_name=promotion.competency_name,
            before=promotion.before,
            before_label=promotion.before.label,
            after=promotion.after,
            after_label=promotion.after.label,
        )


class SelfAssessmentOut(BaseModel):
    message: str
    rubric: list[str]
    reference_html: str


class SubmissionOut(BaseModel):
    passed: bool | None
    first_pass: bool
    message: str
    xp_message: str
    answer_correct: bool | None
    test_run: TestRunOut | None
    rubric: RubricOut | None
    promotions: list[PromotionOut]
    module_ready_message: str
    self_assessment: SelfAssessmentOut | None

    @classmethod
    def from_result(
        cls, result: SubmissionResult, exercise: Exercise, ollama_model: str
    ) -> SubmissionOut:
        outcome = result.outcome
        self_assessment = None
        if result.self_assessment_reason is not None:
            self_assessment = SelfAssessmentOut(
                message=self_assessment_message(result.self_assessment_reason, ollama_model),
                rubric=list(exercise.rubric),
                reference_html=render_markdown(exercise.reference_answer),
            )
        if outcome is None:
            message = ""
        elif outcome.passed:
            message = exercise_passed_message(exercise.title, outcome.first_pass)
        else:
            message = exercise_failed_message(exercise.attempts_count + 1)
        return cls(
            passed=outcome.passed if outcome else None,
            first_pass=bool(outcome and outcome.first_pass),
            message=message,
            xp_message=xp_earned_message(outcome.competency_xp, outcome.activity_xp)
            if outcome
            else "",
            answer_correct=result.answer_correct,
            test_run=TestRunOut.from_result(result.test_run) if result.test_run else None,
            rubric=RubricOut.from_result(result.rubric) if result.rubric else None,
            promotions=[PromotionOut.from_promotion(p) for p in outcome.promotions]
            if outcome
            else [],
            module_ready_message=module_ready_message()
            if outcome and outcome.passed and not outcome.pending_required
            else "",
            self_assessment=self_assessment,
        )


class CompetencyPracticeOut(BaseModel):
    name: str
    exercises_total: int
    exercises_passed: int
    first_try_rate: float | None
    attempts: int
    hints_used: int
    ai_attempts: int

    @classmethod
    def from_practice(cls, practice: CompetencyPractice) -> CompetencyPracticeOut:
        return cls(
            name=practice.name,
            exercises_total=practice.exercises_total,
            exercises_passed=practice.exercises_passed,
            first_try_rate=practice.first_try_rate,
            attempts=practice.attempts,
            hints_used=practice.hints_used,
            ai_attempts=practice.ai_attempts,
        )


class StatsOut(BaseModel):
    xp: XpOut
    exercises_passed: int
    competencies: list[CompetencyPracticeOut]

    @classmethod
    def from_stats(cls, stats: PracticeStats) -> StatsOut:
        return cls(
            xp=XpOut.from_totals(stats.xp),
            exercises_passed=stats.exercises_passed,
            competencies=[CompetencyPracticeOut.from_practice(c) for c in stats.competencies],
        )
