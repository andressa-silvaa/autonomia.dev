from __future__ import annotations

from collections.abc import Iterator
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from hone.api.markdown import render_markdown
from hone.api.schemas import (
    ModuleDetailOut,
    ModuleOut,
    OverviewOut,
    TrackDetailOut,
    TrackSummaryOut,
)
from hone.core.clock import local_today, utc_now
from hone.core.workspace import Workspace, open_workspace
from hone.engines.content import module_key, read_module_content
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
