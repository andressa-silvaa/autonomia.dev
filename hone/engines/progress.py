from __future__ import annotations

import sqlite3
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from hone.core.clock import to_iso_utc
from hone.engines.content import MODULE_KEY_SEPARATOR, module_key


class ModuleStatus(StrEnum):
    LOCKED = "locked"
    AVAILABLE = "available"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


class UnknownModuleError(Exception):
    def __init__(self, reference: str) -> None:
        super().__init__(f"Unknown module: {reference!r}")
        self.reference = reference


class AmbiguousModuleError(Exception):
    def __init__(self, reference: str, candidates: list[str]) -> None:
        super().__init__(f"Module {reference!r} matches: {', '.join(candidates)}")
        self.reference = reference
        self.candidates = candidates


class ModuleLockedError(Exception):
    def __init__(self, module: ModuleView) -> None:
        missing = ", ".join(link.key for link in module.missing_prerequisites)
        super().__init__(f"Module {module.key!r} is locked. Missing: {missing}")
        self.module = module


class RequiredExercisesPendingError(Exception):
    def __init__(self, module: ModuleView, pending_titles: list[str]) -> None:
        super().__init__(f"Module {module.key!r} has required exercises pending")
        self.module = module
        self.pending_titles = pending_titles


@dataclass(frozen=True, slots=True)
class ModuleLink:
    key: str
    title: str


@dataclass(frozen=True, slots=True)
class ModuleView:
    id: int
    track_slug: str
    slug: str
    title: str
    summary: str
    content_path: str | None
    position: int
    status: ModuleStatus
    prerequisites: tuple[ModuleLink, ...]
    missing_prerequisites: tuple[ModuleLink, ...]

    @property
    def key(self) -> str:
        return module_key(self.track_slug, self.slug)

    @property
    def is_open(self) -> bool:
        return self.status is not ModuleStatus.LOCKED


@dataclass(frozen=True, slots=True)
class TrackView:
    slug: str
    name: str
    description: str
    modules: tuple[ModuleView, ...]

    @property
    def completed_count(self) -> int:
        return sum(module.status is ModuleStatus.COMPLETED for module in self.modules)

    @property
    def total_count(self) -> int:
        return len(self.modules)

    @property
    def is_complete(self) -> bool:
        return self.total_count > 0 and self.completed_count == self.total_count


def _decide_status(progress_status: str | None, missing: tuple[ModuleLink, ...]) -> ModuleStatus:
    if progress_status == ModuleStatus.COMPLETED:
        return ModuleStatus.COMPLETED
    if progress_status == ModuleStatus.IN_PROGRESS:
        return ModuleStatus.IN_PROGRESS
    return ModuleStatus.LOCKED if missing else ModuleStatus.AVAILABLE


def list_module_views(conn: sqlite3.Connection, user_id: int) -> list[ModuleView]:
    module_rows = conn.execute(
        "SELECT modules.id, tracks.slug AS track_slug, modules.slug, modules.title, "
        "modules.summary, modules.content_path, modules.position, module_progress.status "
        "FROM modules "
        "JOIN tracks ON tracks.id = modules.track_id "
        "LEFT JOIN module_progress "
        "  ON module_progress.module_id = modules.id AND module_progress.user_id = ? "
        "ORDER BY tracks.name, modules.position",
        (user_id,),
    ).fetchall()

    prerequisite_ids: dict[int, list[int]] = defaultdict(list)
    for row in conn.execute(
        "SELECT module_id, prerequisite_id FROM module_prerequisites ORDER BY prerequisite_id"
    ):
        prerequisite_ids[row["module_id"]].append(row["prerequisite_id"])

    links = {
        row["id"]: ModuleLink(module_key(row["track_slug"], row["slug"]), row["title"])
        for row in module_rows
    }
    completed_ids = {row["id"] for row in module_rows if row["status"] == ModuleStatus.COMPLETED}

    views = []
    for row in module_rows:
        required = tuple(links[pid] for pid in prerequisite_ids[row["id"]])
        missing = tuple(
            links[pid] for pid in prerequisite_ids[row["id"]] if pid not in completed_ids
        )
        views.append(
            ModuleView(
                id=row["id"],
                track_slug=row["track_slug"],
                slug=row["slug"],
                title=row["title"],
                summary=row["summary"],
                content_path=row["content_path"],
                position=row["position"],
                status=_decide_status(row["status"], missing),
                prerequisites=required,
                missing_prerequisites=missing,
            )
        )
    return views


def list_track_views(conn: sqlite3.Connection, user_id: int) -> list[TrackView]:
    modules_by_track: dict[str, list[ModuleView]] = defaultdict(list)
    for module in list_module_views(conn, user_id):
        modules_by_track[module.track_slug].append(module)

    return [
        TrackView(
            row["slug"], row["name"], row["description"], tuple(modules_by_track[row["slug"]])
        )
        for row in conn.execute("SELECT slug, name, description FROM tracks ORDER BY name")
    ]


def find_track_view(conn: sqlite3.Connection, user_id: int, track_slug: str) -> TrackView | None:
    return next(
        (track for track in list_track_views(conn, user_id) if track.slug == track_slug), None
    )


def resolve_module(conn: sqlite3.Connection, user_id: int, reference: str) -> ModuleView:
    modules = list_module_views(conn, user_id)
    reference = reference.strip().strip(MODULE_KEY_SEPARATOR)
    if MODULE_KEY_SEPARATOR in reference:
        matches = [module for module in modules if module.key == reference]
    else:
        matches = [module for module in modules if module.slug == reference]

    if not matches:
        raise UnknownModuleError(reference)
    if len(matches) > 1:
        raise AmbiguousModuleError(reference, [module.key for module in matches])
    return matches[0]


def start_module(conn: sqlite3.Connection, user_id: int, module: ModuleView, now: datetime) -> None:
    if not module.is_open:
        raise ModuleLockedError(module)
    with conn:
        conn.execute(
            "INSERT INTO module_progress (user_id, module_id, status, started_at) "
            "VALUES (?, ?, 'in_progress', ?) ON CONFLICT (user_id, module_id) DO NOTHING",
            (user_id, module.id, to_iso_utc(now)),
        )


def pending_required_exercises(conn: sqlite3.Connection, user_id: int, module_id: int) -> list[str]:
    rows = conn.execute(
        "SELECT exercises.title FROM exercises "
        "LEFT JOIN exercise_progress ON exercise_progress.exercise_id = exercises.id "
        "AND exercise_progress.user_id = ? "
        "WHERE exercises.module_id = ? AND exercises.required = 1 AND exercises.retired = 0 "
        "AND exercise_progress.passed_at IS NULL ORDER BY exercises.position",
        (user_id, module_id),
    )
    return [row["title"] for row in rows]


def complete_module(
    conn: sqlite3.Connection, user_id: int, module: ModuleView, now: datetime
) -> list[ModuleView]:
    if module.missing_prerequisites:
        raise ModuleLockedError(module)
    if module.status is ModuleStatus.COMPLETED:
        return []
    pending = pending_required_exercises(conn, user_id, module.id)
    if pending:
        raise RequiredExercisesPendingError(module, pending)

    locked_before = {view.id for view in list_module_views(conn, user_id) if not view.is_open}
    timestamp = to_iso_utc(now)
    with conn:
        conn.execute(
            "INSERT INTO module_progress (user_id, module_id, status, started_at, completed_at) "
            "VALUES (?, ?, 'completed', ?, ?) "
            "ON CONFLICT (user_id, module_id) DO UPDATE SET "
            "status = 'completed', completed_at = excluded.completed_at",
            (user_id, module.id, timestamp, timestamp),
        )
    return [
        view
        for view in list_module_views(conn, user_id)
        if view.id in locked_before and view.is_open
    ]
