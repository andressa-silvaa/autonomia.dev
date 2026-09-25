from __future__ import annotations

from fastapi import APIRouter

from hone.api.dependencies import WorkspaceDep
from hone.api.exercise_schemas import (
    DraftIn,
    ExerciseDetailOut,
    HintOut,
    SelfAssessmentIn,
    StatsOut,
    SubmissionIn,
    SubmissionOut,
)
from hone.api.schemas import MessageOut
from hone.core.clock import utc_now
from hone.core.models import AnswerFormat
from hone.core.workspace import Workspace
from hone.engines.exercises import (
    Exercise,
    current_draft,
    list_attempts,
    resolve_exercise,
    reveal_hint,
    save_draft,
    start_exercise,
)
from hone.engines.metrics import build_practice_stats
from hone.engines.progress import ModuleView, resolve_module
from hone.engines.submissions import (
    submit_answer_key,
    submit_code,
    submit_self_assessment,
    submit_text,
)

router = APIRouter(prefix="/api")


def _started(workspace: Workspace, slug: str) -> tuple[Exercise, ModuleView]:
    settings = workspace.settings
    exercise = resolve_exercise(workspace.conn, workspace.user_id, slug)
    module = resolve_module(workspace.conn, workspace.user_id, exercise.module_key)
    start_exercise(
        workspace.conn,
        workspace.user_id,
        exercise,
        module,
        settings.exercises_dir,
        settings.workspace_dir,
        utc_now(),
    )
    return resolve_exercise(workspace.conn, workspace.user_id, slug), module


@router.get(
    "/exercises/{slug}",
    response_model=ExerciseDetailOut,
    description="Statement, your draft, revealed hints and attempt history.",
)
def get_exercise(slug: str, workspace: WorkspaceDep) -> ExerciseDetailOut:
    settings = workspace.settings
    exercise = resolve_exercise(workspace.conn, workspace.user_id, slug)
    module = resolve_module(workspace.conn, workspace.user_id, exercise.module_key)
    return ExerciseDetailOut.from_exercise(
        exercise,
        module.is_open,
        current_draft(settings.exercises_dir, settings.workspace_dir, exercise),
        list_attempts(workspace.conn, workspace.user_id, exercise.id),
    )


@router.put(
    "/exercises/{slug}/draft",
    response_model=MessageOut,
    description="Saves what you are writing, so nothing is lost if the page closes.",
)
def put_draft(slug: str, body: DraftIn, workspace: WorkspaceDep) -> MessageOut:
    settings = workspace.settings
    exercise = resolve_exercise(workspace.conn, workspace.user_id, slug)
    module = resolve_module(workspace.conn, workspace.user_id, exercise.module_key)
    save_draft(
        workspace.conn,
        workspace.user_id,
        exercise,
        module,
        settings.exercises_dir,
        settings.workspace_dir,
        body.content,
        utc_now(),
    )
    return MessageOut(message="rascunho salvo")


@router.post(
    "/exercises/{slug}/hints",
    response_model=HintOut,
    description="Reveals the next hint. Each hint lowers the XP of a first pass.",
)
def post_hint(slug: str, workspace: WorkspaceDep) -> HintOut:
    exercise, _ = _started(workspace, slug)
    hint = reveal_hint(workspace.conn, workspace.user_id, exercise, utc_now())
    return HintOut(hint=hint, number=exercise.hints_revealed + 1, total=len(exercise.hints))


@router.post(
    "/exercises/{slug}/submissions",
    response_model=SubmissionOut,
    description="Submits an answer: checked against the answer key, run against the tests, "
    "or graded by Ollama. Without Ollama, asks for a self-assessment instead.",
)
def post_submission(slug: str, body: SubmissionIn, workspace: WorkspaceDep) -> SubmissionOut:
    settings = workspace.settings
    conn, user_id, now = workspace.conn, workspace.user_id, utc_now()
    exercise, module = _started(workspace, slug)
    match exercise.answer_format:
        case AnswerFormat.CODE:
            result = submit_code(
                conn, settings, user_id, exercise, module, body.content, body.used_ai, now
            )
        case AnswerFormat.TEXT:
            result = submit_text(
                conn, settings, user_id, exercise, module, body.content, body.used_ai, now
            )
        case _:
            result = submit_answer_key(conn, user_id, exercise, body.answer, body.used_ai, now)
    return SubmissionOut.from_result(result, exercise, settings.ollama_model)


@router.post(
    "/exercises/{slug}/self-assessments",
    response_model=SubmissionOut,
    description="Grades a written answer with your own judgment of each rubric criterion.",
)
def post_self_assessment(
    slug: str, body: SelfAssessmentIn, workspace: WorkspaceDep
) -> SubmissionOut:
    settings = workspace.settings
    exercise, _ = _started(workspace, slug)
    result = submit_self_assessment(
        workspace.conn, settings, workspace.user_id, exercise, body.met, body.used_ai, utc_now()
    )
    return SubmissionOut.from_result(result, exercise, settings.ollama_model)


@router.get(
    "/stats", response_model=StatsOut, description="XP and practice metrics per competency."
)
def get_stats(workspace: WorkspaceDep) -> StatsOut:
    return StatsOut.from_stats(build_practice_stats(workspace.conn, workspace.user_id))
