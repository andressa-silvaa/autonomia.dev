from __future__ import annotations

from fastapi import APIRouter

from hone.api.dependencies import WorkspaceDep
from hone.api.schemas import (
    CheckinIn,
    CheckinResultOut,
    CompletionOut,
    MessageOut,
    ModuleOut,
    SessionOut,
    SessionStartIn,
    SessionStopIn,
    StreakOut,
)
from hone.core.clock import local_today, utc_now
from hone.engines.checkins import check_in, get_streak
from hone.engines.content import module_key
from hone.engines.progress import (
    ModuleStatus,
    complete_module,
    find_track_view,
    resolve_module,
    start_module,
)
from hone.engines.sessions import start_session, stop_session
from hone.voice import (
    checkin_saved_message,
    module_completed_message,
    session_stopped_message,
    track_completed_message,
)

router = APIRouter(prefix="/api")


@router.post(
    "/checkin", response_model=CheckinResultOut, description="Records today's study intention."
)
def post_checkin(body: CheckinIn, workspace: WorkspaceDep) -> CheckinResultOut:
    today = local_today()
    check_in(workspace.conn, workspace.user_id, body.intention, today, utc_now())
    streak = get_streak(workspace.conn, workspace.user_id, today)
    return CheckinResultOut(
        message=checkin_saved_message(streak), streak=StreakOut.from_streak(streak)
    )


@router.post(
    "/sessions",
    response_model=SessionOut,
    description="Starts a timed study session, optionally on a module.",
)
def post_session(body: SessionStartIn, workspace: WorkspaceDep) -> SessionOut:
    now = utc_now()
    module_id = None
    if body.module_key:
        module = resolve_module(workspace.conn, workspace.user_id, body.module_key)
        start_module(workspace.conn, workspace.user_id, module, now)
        module_id = module.id
    session = start_session(workspace.conn, workspace.user_id, module_id, now)
    return SessionOut.from_session(session)


@router.post(
    "/sessions/stop", response_model=MessageOut, description="Stops the running study session."
)
def post_session_stop(body: SessionStopIn, workspace: WorkspaceDep) -> MessageOut:
    session = stop_session(workspace.conn, workspace.user_id, body.notes, utc_now())
    return MessageOut(message=session_stopped_message(session.elapsed_minutes(utc_now())))


@router.post(
    "/tracks/{track_slug}/modules/{module_slug}/complete",
    response_model=CompletionOut,
    description="Completes a module once its prerequisites and required exercises are done.",
)
def post_module_complete(
    track_slug: str, module_slug: str, workspace: WorkspaceDep
) -> CompletionOut:
    module = resolve_module(workspace.conn, workspace.user_id, module_key(track_slug, module_slug))
    if module.status is ModuleStatus.COMPLETED:
        return CompletionOut(
            message=f"“{module.title}” já estava concluído.", unlocked=[], track_message=None
        )
    unlocked = complete_module(workspace.conn, workspace.user_id, module, utc_now())
    track = find_track_view(workspace.conn, workspace.user_id, track_slug)
    return CompletionOut(
        message=module_completed_message(module.title),
        unlocked=[ModuleOut.from_view(view) for view in unlocked],
        track_message=track_completed_message(track.name)
        if track is not None and track.is_complete
        else None,
    )
