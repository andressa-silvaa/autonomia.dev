from __future__ import annotations

from fastapi import APIRouter, HTTPException

from hone.api.dependencies import WorkspaceDep
from hone.api.exercise_schemas import ExerciseSummaryOut, XpOut
from hone.api.markdown import render_markdown
from hone.api.schemas import (
    ModuleDetailOut,
    ModuleOut,
    OverviewOut,
    TrackDetailOut,
    TrackSummaryOut,
)
from hone.core.clock import local_today, utc_now
from hone.engines.content import module_key, read_module_content
from hone.engines.exercises import list_exercises
from hone.engines.overview import build_overview
from hone.engines.progress import (
    find_track_view,
    list_track_views,
    pending_required_exercises,
    resolve_module,
)
from hone.engines.xp import xp_totals

router = APIRouter(prefix="/api")


@router.get(
    "/overview",
    response_model=OverviewOut,
    description="Streak, check-in, session, XP and progress for today.",
)
def get_overview(workspace: WorkspaceDep) -> OverviewOut:
    overview = build_overview(workspace.conn, workspace.user_id, local_today(), utc_now())
    xp = XpOut.from_totals(xp_totals(workspace.conn, workspace.user_id))
    return OverviewOut.from_overview(workspace.user.name, overview, xp)


@router.get(
    "/tracks", response_model=list[TrackSummaryOut], description="All tracks with progress."
)
def get_tracks(workspace: WorkspaceDep) -> list[TrackSummaryOut]:
    return [
        TrackSummaryOut.from_view(track)
        for track in list_track_views(workspace.conn, workspace.user_id)
    ]


@router.get(
    "/tracks/{track_slug}", response_model=TrackDetailOut, description="A track and its modules."
)
def get_track(track_slug: str, workspace: WorkspaceDep) -> TrackDetailOut:
    track = find_track_view(workspace.conn, workspace.user_id, track_slug)
    if track is None:
        raise HTTPException(status_code=404, detail=f"Track {track_slug!r} not found")
    return TrackDetailOut.from_track(track)


@router.get(
    "/tracks/{track_slug}/modules/{module_slug}",
    response_model=ModuleDetailOut,
    description="Module metadata, rendered content and exercises. "
    "Locked modules come without content.",
)
def get_module(track_slug: str, module_slug: str, workspace: WorkspaceDep) -> ModuleDetailOut:
    module = resolve_module(workspace.conn, workspace.user_id, module_key(track_slug, module_slug))
    track = find_track_view(workspace.conn, workspace.user_id, track_slug)
    content_html = ""
    if module.is_open:
        markdown_text = read_module_content(
            workspace.settings.content_dir, module.content_path or ""
        )
        content_html = render_markdown(markdown_text)
    return ModuleDetailOut(
        **ModuleOut.from_view(module).model_dump(),
        track_name=track.name if track else track_slug,
        content_html=content_html,
        exercises=[
            ExerciseSummaryOut.from_exercise(exercise)
            for exercise in list_exercises(workspace.conn, workspace.user_id, module.id)
        ],
        pending_required=pending_required_exercises(workspace.conn, workspace.user_id, module.id),
    )
