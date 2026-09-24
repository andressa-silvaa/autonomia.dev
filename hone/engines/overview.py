from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import date, datetime, timedelta

from hone.engines.checkins import Checkin, Streak, find_checkin, get_streak
from hone.engines.knowledge import LearningPath, find_goal_path
from hone.engines.progress import ModuleStatus, ModuleView, TrackView, list_track_views
from hone.engines.sessions import SessionView, find_active_session, study_minutes_by_day

DEFAULT_HISTORY_DAYS = 14
MAX_NEXT_MODULES = 3


@dataclass(frozen=True, slots=True)
class Overview:
    today: date
    streak: Streak
    todays_checkin: Checkin | None
    active_session: SessionView | None
    study_minutes: list[tuple[date, int]]
    tracks: list[TrackView]
    next_modules: list[ModuleView]
    goal_path: LearningPath | None


def _pick_next_modules(tracks: list[TrackView], goal_path: LearningPath | None) -> list[ModuleView]:
    if goal_path is not None and not goal_path.is_reached:
        open_steps = [step.module for step in goal_path.steps if step.module.is_open]
        return open_steps[:MAX_NEXT_MODULES]
    modules = [module for track in tracks for module in track.modules]
    in_progress = [m for m in modules if m.status is ModuleStatus.IN_PROGRESS]
    available = [m for m in modules if m.status is ModuleStatus.AVAILABLE]
    return (in_progress + available)[:MAX_NEXT_MODULES]


def build_overview(
    conn: sqlite3.Connection,
    user_id: int,
    today: date,
    now: datetime,
    history_days: int = DEFAULT_HISTORY_DAYS,
) -> Overview:
    tracks = list_track_views(conn, user_id)
    goal_path = find_goal_path(conn, user_id)
    first_day = today - timedelta(days=history_days - 1)
    return Overview(
        today=today,
        streak=get_streak(conn, user_id, today),
        todays_checkin=find_checkin(conn, user_id, today),
        active_session=find_active_session(conn, user_id),
        study_minutes=study_minutes_by_day(conn, user_id, first_day, today, now),
        tracks=tracks,
        next_modules=_pick_next_modules(tracks, goal_path),
        goal_path=goal_path,
    )
