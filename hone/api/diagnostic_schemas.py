from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from hone.api.markdown import render_markdown
from hone.core.models import AnswerConfidence, Mastery
from hone.engines.diagnostic import (
    AnswerOutcome,
    CompetencyResult,
    DiagnosticReport,
    DiagnosticRun,
    Question,
)
from hone.voice import answer_feedback_message, diagnostic_finished_message


class DiagnosticQuestionOut(BaseModel):
    id: int
    competency_name: str
    kind_label: str
    prompt_html: str
    options: list[str]
    is_choice: bool

    @classmethod
    def from_question(cls, question: Question) -> DiagnosticQuestionOut:
        return cls(
            id=question.id,
            competency_name=question.competency_name,
            kind_label=question.kind.label,
            prompt_html=render_markdown(question.prompt),
            options=list(question.options),
            is_choice=question.is_choice,
        )


class DiagnosticStateOut(BaseModel):
    answered: int
    total: int
    question: DiagnosticQuestionOut | None

    @classmethod
    def from_run(cls, run: DiagnosticRun, question: Question | None) -> DiagnosticStateOut:
        return cls(
            answered=run.answered_count,
            total=run.total_count,
            question=DiagnosticQuestionOut.from_question(question) if question else None,
        )


class CompetencyResultOut(BaseModel):
    competency_name: str
    assessed: Mastery
    assessed_label: str
    assessed_rank: int
    correct: int
    guessed: int
    answered: int
    is_solid: bool

    @classmethod
    def from_result(cls, result: CompetencyResult) -> CompetencyResultOut:
        return cls(
            competency_name=result.competency_name,
            assessed=result.assessed,
            assessed_label=result.assessed.label,
            assessed_rank=result.assessed.rank,
            correct=result.correct_count,
            guessed=result.guessed_count,
            answered=result.answered_count,
            is_solid=result.is_solid,
        )


class DiagnosticReportOut(BaseModel):
    finished_at: datetime
    message: str
    max_mastery_rank: int
    results: list[CompetencyResultOut]

    @classmethod
    def from_report(cls, report: DiagnosticReport) -> DiagnosticReportOut:
        solid = sum(result.is_solid for result in report.results)
        return cls(
            finished_at=report.finished_at,
            message=diagnostic_finished_message(solid, len(report.results)),
            max_mastery_rank=Mastery.MASTERY.rank,
            results=[CompetencyResultOut.from_result(result) for result in report.results],
        )


class DiagnosticAnswerIn(BaseModel):
    question_id: int
    answer: str = ""
    confidence: AnswerConfidence
    duration_seconds: int | None = None


class DiagnosticAnswerOut(BaseModel):
    is_correct: bool
    message: str
    correct_answer: str | None
    explanation: str
    next_state: DiagnosticStateOut | None
    report: DiagnosticReportOut | None

    @classmethod
    def build(
        cls,
        outcome: AnswerOutcome,
        next_state: DiagnosticStateOut | None,
        report: DiagnosticReport | None,
    ) -> DiagnosticAnswerOut:
        return cls(
            is_correct=outcome.is_correct,
            message=answer_feedback_message(outcome),
            correct_answer=None if outcome.is_correct else outcome.correct_answer,
            explanation=outcome.explanation,
            next_state=next_state,
            report=DiagnosticReportOut.from_report(report) if report else None,
        )
