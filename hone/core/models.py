from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class Mastery(StrEnum):
    NOT_STUDIED = "not_studied"
    UNKNOWN = "unknown"
    BEGINNING = "beginning"
    RECOGNIZES = "recognizes"
    CAN_APPLY = "can_apply"
    CAN_EXPLAIN = "can_explain"
    CAN_TEACH = "can_teach"
    MASTERY = "mastery"

    @property
    def rank(self) -> int:
        return list(Mastery).index(self)

    @property
    def label(self) -> str:
        return MASTERY_LABELS[self]


MASTERY_LABELS = {
    Mastery.NOT_STUDIED: "não estudado",
    Mastery.UNKNOWN: "desconhecido",
    Mastery.BEGINNING: "começando",
    Mastery.RECOGNIZES: "reconhece",
    Mastery.CAN_APPLY: "consegue aplicar",
    Mastery.CAN_EXPLAIN: "consegue explicar",
    Mastery.CAN_TEACH: "consegue ensinar",
    Mastery.MASTERY: "domínio",
}


class ExerciseKind(StrEnum):
    QUIZ = "quiz"
    CODE_FROM_SCRATCH = "code"
    COMPLETE_CODE = "complete"
    DEBUG = "debug"
    CODE_READING = "code_reading"
    CODE_REVIEW = "code_review"
    REFACTORING = "refactoring"
    OPEN_ANSWER = "open"
    CONCEPT_EXPLANATION = "explanation"
    DOCUMENTATION = "documentation"
    PRESENTATION = "presentation"
    SURPRISE = "surprise"


class GradingMethod(StrEnum):
    AUTOMATED_TESTS = "auto"
    LOCAL_AI = "ollama"
    SELF_ASSESSMENT = "self"


class ProjectKind(StrEnum):
    INTEGRATOR = "integrator"
    SURPRISE = "surprise"


@dataclass(slots=True)
class User:
    name: str
    id: int | None = None
    created_at: str | None = None


@dataclass(slots=True)
class Area:
    slug: str
    name: str
    description: str = ""
    id: int | None = None


@dataclass(slots=True)
class Competency:
    area_id: int
    slug: str
    name: str
    description: str = ""
    id: int | None = None


@dataclass(slots=True)
class Track:
    slug: str
    name: str
    description: str = ""
    id: int | None = None


@dataclass(slots=True)
class Module:
    track_id: int
    slug: str
    title: str
    summary: str = ""
    content_path: str | None = None
    position: int = 0
    id: int | None = None


@dataclass(slots=True)
class Exercise:
    module_id: int
    slug: str
    title: str
    kind: ExerciseKind
    grading: GradingMethod
    prompt: str
    difficulty: int = 1
    xp: int = 10
    id: int | None = None


@dataclass(slots=True)
class Project:
    slug: str
    title: str
    kind: ProjectKind
    track_id: int | None = None
    description: str = ""
    id: int | None = None


@dataclass(slots=True)
class UserCompetency:
    user_id: int
    competency_id: int
    mastery: Mastery = Mastery.NOT_STUDIED
    updated_at: str | None = None


@dataclass(slots=True)
class StudySession:
    user_id: int
    module_id: int | None = None
    started_at: str | None = None
    ended_at: str | None = None
    notes: str = ""
    id: int | None = None


@dataclass(slots=True)
class Attempt:
    user_id: int
    exercise_id: int
    session_id: int | None = None
    submitted_at: str | None = None
    answer: str = ""
    score: float | None = None
    feedback: str = ""
    duration_seconds: int | None = None
    hints_used: int = 0
    used_ai: bool = False
    id: int | None = None


SM2_INITIAL_EASINESS = 2.5


@dataclass(slots=True)
class Review:
    user_id: int
    competency_id: int
    easiness: float = SM2_INITIAL_EASINESS
    interval_days: int = 0
    repetitions: int = 0
    due_on: str | None = None
    last_reviewed_at: str | None = None
    id: int | None = None
