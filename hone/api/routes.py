from __future__ import annotations

from collections.abc import Iterator
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from hone.api.markdown import render_markdown
from hone.api.schemas import (
    AreaMapOut,
    DiagnosticProgressOut,
    KnowledgeMapOut,
    LearningPathOut,
    ModuleDetailOut,
    ModuleOut,
    OverviewOut,
    TrackDetailOut,
    TrackSummaryOut,
)
from hone.core.clock import local_today, utc_now
from hone.core.models import Mastery
from hone.core.workspace import Workspace, open_workspace
from hone.engines.content import module_key, read_module_content
from hone.engines.diagnostic import find_open_run, last_finished_at
from hone.engines.knowledge import (
    build_knowledge_map,
    find_goal_path,
    list_assessed_gaps,
    list_module_levels,
)
from hone.engines.overview import build_overview
from hone.engines.progress import find_track_view, list_track_views, resolve_module

router = APIRouter(prefix="/api")


def get_workspace() -> Iterator[Workspace]:
    with open_workspace(allow_cross_thread=True) as workspace:
        yield workspace


WorkspaceDep = Annotated[Workspace, Depends(get_workspace)]


@router.get(
    "/overview",
    response_model=OverviewOut,
    description="Streak, check-in, session and progress for today.",
)
def get_overview(workspace: WorkspaceDep) -> OverviewOut:
    overview = build_overview(workspace.conn, workspace.user_id, local_today(), utc_now())
    return OverviewOut.from_overview(workspace.user.name, overview)


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
    description="Module metadata and rendered content. Locked modules come without content.",
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
    )


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


@router.get(
    "/learning-path",
    response_model=LearningPathOut,
    description="Recommended sequence and gaps up to the current goal. "
    "Without a goal, only the gaps found by the diagnostic.",
)
def get_learning_path(workspace: WorkspaceDep) -> LearningPathOut:
    path = find_goal_path(workspace.conn, workspace.user_id)
    if path is None:
        return LearningPathOut.without_goal(list_assessed_gaps(workspace.conn, workspace.user_id))
    return LearningPathOut.from_path(path)


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
