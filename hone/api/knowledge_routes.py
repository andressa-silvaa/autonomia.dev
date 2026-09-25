from __future__ import annotations

from fastapi import APIRouter

from hone.api.dependencies import WorkspaceDep
from hone.api.diagnostic_schemas import (
    DiagnosticAnswerIn,
    DiagnosticAnswerOut,
    DiagnosticReportOut,
    DiagnosticStateOut,
)
from hone.api.schemas import (
    AreaMapOut,
    DiagnosticProgressOut,
    GoalIn,
    GoalOut,
    KnowledgeMapOut,
    LearningPathOut,
    ModuleOut,
)
from hone.core.clock import utc_now
from hone.core.models import Mastery
from hone.engines.diagnostic import (
    NoOpenDiagnosticError,
    find_open_run,
    finish_run,
    last_finished_at,
    latest_report,
    next_question,
    pending_question,
    record_answer,
    start_or_resume_run,
)
from hone.engines.knowledge import (
    build_knowledge_map,
    build_learning_path,
    clear_goal,
    find_goal_path,
    list_assessed_gaps,
    list_module_levels,
    set_goal,
)
from hone.engines.progress import resolve_module
from hone.voice import goal_set_message

router = APIRouter(prefix="/api")


@router.get(
    "/knowledge-map",
    response_model=KnowledgeMapOut,
    description="Mastery level of every competency, grouped by area, plus diagnostic status.",
)
def get_knowledge_map(workspace: WorkspaceDep) -> KnowledgeMapOut:
    open_run = find_open_run(workspace.conn, workspace.user_id)
    return KnowledgeMapOut(
        max_mastery_rank=Mastery.MASTERY.rank,
        areas=[
            AreaMapOut.from_area(area)
            for area in build_knowledge_map(workspace.conn, workspace.user_id)
        ],
        last_diagnostic_at=last_finished_at(workspace.conn, workspace.user_id),
        open_diagnostic=DiagnosticProgressOut.from_run(open_run) if open_run else None,
    )


def _current_path(workspace: WorkspaceDep) -> LearningPathOut:
    path = find_goal_path(workspace.conn, workspace.user_id)
    if path is None:
        return LearningPathOut.without_goal(list_assessed_gaps(workspace.conn, workspace.user_id))
    return LearningPathOut.from_path(path)


@router.get(
    "/learning-path",
    response_model=LearningPathOut,
    description="Recommended sequence and gaps up to the current goal. "
    "Without a goal, only the gaps found by the diagnostic.",
)
def get_learning_path(workspace: WorkspaceDep) -> LearningPathOut:
    return _current_path(workspace)


@router.put("/goal", response_model=GoalOut, description="Sets the module you want to reach.")
def put_goal(body: GoalIn, workspace: WorkspaceDep) -> GoalOut:
    module = resolve_module(workspace.conn, workspace.user_id, body.module_key)
    set_goal(workspace.conn, workspace.user_id, module, utc_now())
    path = build_learning_path(workspace.conn, workspace.user_id, module)
    return GoalOut(message=goal_set_message(module.title), path=LearningPathOut.from_path(path))


@router.delete("/goal", response_model=LearningPathOut, description="Removes the current goal.")
def delete_goal(workspace: WorkspaceDep) -> LearningPathOut:
    clear_goal(workspace.conn, workspace.user_id)
    return _current_path(workspace)


@router.get(
    "/module-levels",
    response_model=list[list[ModuleOut]],
    description="Modules grouped by prerequisite depth: each level only depends on earlier ones.",
)
def get_module_levels(workspace: WorkspaceDep) -> list[list[ModuleOut]]:
    return [
        [ModuleOut.from_view(module) for module in level]
        for level in list_module_levels(workspace.conn, workspace.user_id)
    ]


@router.get(
    "/diagnostic",
    response_model=DiagnosticStateOut | None,
    description="The diagnostic in progress and its next question, or null.",
)
def get_diagnostic(workspace: WorkspaceDep) -> DiagnosticStateOut | None:
    run = find_open_run(workspace.conn, workspace.user_id)
    if run is None:
        return None
    return DiagnosticStateOut.from_run(run, next_question(workspace.conn, run.id))


@router.post(
    "/diagnostic",
    response_model=DiagnosticStateOut,
    description="Starts a diagnostic, or resumes the one in progress.",
)
def post_diagnostic(workspace: WorkspaceDep) -> DiagnosticStateOut:
    run, _ = start_or_resume_run(workspace.conn, workspace.user_id, utc_now())
    return DiagnosticStateOut.from_run(run, next_question(workspace.conn, run.id))


@router.post(
    "/diagnostic/answers",
    response_model=DiagnosticAnswerOut,
    description="Answers the pending question. The last answer finishes the diagnostic.",
)
def post_diagnostic_answer(
    body: DiagnosticAnswerIn, workspace: WorkspaceDep
) -> DiagnosticAnswerOut:
    conn, user_id = workspace.conn, workspace.user_id
    run = find_open_run(conn, user_id)
    if run is None:
        raise NoOpenDiagnosticError()
    question = pending_question(conn, run.id, body.question_id)
    outcome = record_answer(
        conn, run.id, question, body.answer, body.confidence, body.duration_seconds, utc_now()
    )

    following = next_question(conn, run.id)
    if following is None:
        return DiagnosticAnswerOut.build(outcome, None, finish_run(conn, user_id, utc_now()))
    updated = find_open_run(conn, user_id)
    assert updated is not None
    return DiagnosticAnswerOut.build(outcome, DiagnosticStateOut.from_run(updated, following), None)


@router.get(
    "/diagnostic/report",
    response_model=DiagnosticReportOut,
    description="Result of the latest finished diagnostic.",
)
def get_diagnostic_report(workspace: WorkspaceDep) -> DiagnosticReportOut:
    return DiagnosticReportOut.from_report(latest_report(workspace.conn, workspace.user_id))
