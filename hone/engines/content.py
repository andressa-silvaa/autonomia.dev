from __future__ import annotations

import sqlite3
from collections import Counter
from dataclasses import dataclass
from graphlib import CycleError, TopologicalSorter
from pathlib import Path

from hone.engines.question_bank import (
    QuestionDefinition,
    parse_questions,
    sync_questions,
    validate_questions,
)
from hone.engines.toml_tables import TableReader, read_tables, read_toml

CATALOG_FILENAME = "catalog.toml"
TRACKS_DIRNAME = "tracks"
TRACK_FILENAME = "track.toml"
MODULE_KEY_SEPARATOR = "/"


class ContentError(Exception):
    def __init__(self, problems: list[str]) -> None:
        super().__init__("Invalid content:\n" + "\n".join(f"- {problem}" for problem in problems))
        self.problems = problems


class ContentFileMissingError(Exception):
    pass


@dataclass(frozen=True, slots=True)
class AreaDefinition:
    slug: str
    name: str
    description: str


@dataclass(frozen=True, slots=True)
class CompetencyDefinition:
    slug: str
    area_slug: str
    name: str
    description: str


@dataclass(frozen=True, slots=True)
class ModuleDefinition:
    track_slug: str
    slug: str
    title: str
    summary: str
    content_path: str
    requires: tuple[str, ...]
    competencies: tuple[str, ...]

    @property
    def key(self) -> str:
        return module_key(self.track_slug, self.slug)


@dataclass(frozen=True, slots=True)
class TrackDefinition:
    slug: str
    name: str
    description: str
    modules: tuple[ModuleDefinition, ...]


@dataclass(frozen=True, slots=True)
class ContentDefinition:
    areas: tuple[AreaDefinition, ...]
    competencies: tuple[CompetencyDefinition, ...]
    tracks: tuple[TrackDefinition, ...]
    questions: tuple[QuestionDefinition, ...] = ()

    @property
    def modules(self) -> tuple[ModuleDefinition, ...]:
        return tuple(module for track in self.tracks for module in track.modules)


@dataclass(frozen=True, slots=True)
class SyncReport:
    areas: int
    competencies: int
    tracks: int
    modules: int
    orphan_modules: tuple[str, ...]
    questions: int = 0
    retired_questions: tuple[str, ...] = ()


def module_key(track_slug: str, module_slug: str) -> str:
    return f"{track_slug}{MODULE_KEY_SEPARATOR}{module_slug}"


def qualify_module_reference(reference: str, current_track_slug: str) -> str:
    if MODULE_KEY_SEPARATOR in reference:
        return reference
    return module_key(current_track_slug, reference)


def tracks_root(content_dir: Path) -> Path:
    return content_dir / TRACKS_DIRNAME


def read_module_content(content_dir: Path, content_path: str) -> str:
    path = tracks_root(content_dir) / content_path
    if not path.is_file():
        raise ContentFileMissingError(f"Content file not found: {path}")
    return path.read_text(encoding="utf-8")


def _parse_catalog(
    content_dir: Path, problems: list[str]
) -> tuple[tuple[AreaDefinition, ...], tuple[CompetencyDefinition, ...]]:
    path = content_dir / CATALOG_FILENAME
    document = read_toml(path, problems)

    areas = []
    for index, table in enumerate(read_tables(document, "areas", path, problems), start=1):
        reader = TableReader(table, f"{path.name} area #{index}", problems)
        areas.append(
            AreaDefinition(
                reader.text("slug"), reader.text("name"), reader.text("description", required=False)
            )
        )

    competencies = []
    for index, table in enumerate(read_tables(document, "competencies", path, problems), start=1):
        reader = TableReader(table, f"{path.name} competency #{index}", problems)
        competencies.append(
            CompetencyDefinition(
                reader.text("slug"),
                reader.text("area"),
                reader.text("name"),
                reader.text("description", required=False),
            )
        )
    return tuple(areas), tuple(competencies)


def _parse_module(
    table: dict, track_slug: str, track_dir: Path, location: str, problems: list[str]
) -> ModuleDefinition:
    reader = TableReader(table, location, problems)
    content_file = reader.text("content")
    module = ModuleDefinition(
        track_slug=track_slug,
        slug=reader.text("slug"),
        title=reader.text("title"),
        summary=reader.text("summary", required=False),
        content_path=f"{track_dir.name}/{content_file}",
        requires=tuple(
            qualify_module_reference(reference, track_slug)
            for reference in reader.text_list("requires")
        ),
        competencies=reader.text_list("competencies"),
    )
    if content_file:
        _check_content_file(track_dir, content_file, location, problems)
    return module


def _check_content_file(
    track_dir: Path, content_file: str, location: str, problems: list[str]
) -> None:
    resolved = (track_dir / content_file).resolve()
    if not resolved.is_relative_to(track_dir.resolve()):
        problems.append(f"{location}: content '{content_file}' must stay inside {track_dir.name}/")
    elif not resolved.is_file():
        problems.append(f"{location}: content file '{content_file}' not found")


def _parse_track(track_dir: Path, problems: list[str]) -> TrackDefinition | None:
    path = track_dir / TRACK_FILENAME
    document = read_toml(path, problems)
    header = document.get("track")
    location = f"{track_dir.name}/{TRACK_FILENAME}"
    if not isinstance(header, dict):
        problems.append(f"{location}: missing [track] table")
        return None

    reader = TableReader(header, location, problems)
    slug = reader.text("slug")
    if slug and slug != track_dir.name:
        problems.append(
            f"{location}: track slug '{slug}' must match folder name '{track_dir.name}'"
        )

    modules = tuple(
        _parse_module(table, slug, track_dir, f"{location} module #{index}", problems)
        for index, table in enumerate(read_tables(document, "modules", path, problems), start=1)
    )
    return TrackDefinition(
        slug, reader.text("name"), reader.text("description", required=False), modules
    )


def _duplicates(values: list[str]) -> list[str]:
    return sorted(value for value, count in Counter(values).items() if value and count > 1)


def _validate_references(content: ContentDefinition, problems: list[str]) -> None:
    area_slugs = {area.slug for area in content.areas}
    competency_slugs = {competency.slug for competency in content.competencies}
    module_keys = {module.key for module in content.modules}

    for label, values in (
        ("area", [area.slug for area in content.areas]),
        ("competency", [competency.slug for competency in content.competencies]),
        ("track", [track.slug for track in content.tracks]),
        ("module", [module.key for module in content.modules]),
    ):
        for duplicate in _duplicates(values):
            problems.append(f"duplicate {label} slug '{duplicate}'")

    for competency in content.competencies:
        if competency.area_slug and competency.area_slug not in area_slugs:
            problems.append(
                f"competency '{competency.slug}' uses unknown area '{competency.area_slug}'"
            )

    for module in content.modules:
        for competency_slug in module.competencies:
            if competency_slug not in competency_slugs:
                problems.append(
                    f"module '{module.key}' uses unknown competency '{competency_slug}'"
                )
        for prerequisite in module.requires:
            if prerequisite == module.key:
                problems.append(f"module '{module.key}' cannot require itself")
            elif prerequisite not in module_keys:
                problems.append(f"module '{module.key}' requires unknown module '{prerequisite}'")


def _validate_acyclic(content: ContentDefinition, problems: list[str]) -> None:
    graph = {module.key: set(module.requires) for module in content.modules}
    try:
        TopologicalSorter(graph).prepare()
    except CycleError as exc:
        cycle = exc.args[1]
        problems.append("prerequisite cycle: " + " -> ".join(cycle))


def load_content(content_dir: Path) -> ContentDefinition:
    problems: list[str] = []
    areas, competencies = _parse_catalog(content_dir, problems)

    tracks = []
    root = tracks_root(content_dir)
    track_dirs = (
        sorted(path.parent for path in root.glob(f"*/{TRACK_FILENAME}")) if root.is_dir() else []
    )
    for track_dir in track_dirs:
        track = _parse_track(track_dir, problems)
        if track is not None:
            tracks.append(track)

    questions = parse_questions(content_dir, problems)
    content = ContentDefinition(areas, competencies, tuple(tracks), questions)
    if not problems:
        _validate_references(content, problems)
        validate_questions(questions, {c.slug for c in competencies}, problems)
    if not problems:
        _validate_acyclic(content, problems)
    if problems:
        raise ContentError(problems)
    return content


def _upsert_catalog(conn: sqlite3.Connection, content: ContentDefinition) -> None:
    conn.executemany(
        "INSERT INTO areas (slug, name, description) VALUES (?, ?, ?) "
        "ON CONFLICT (slug) DO UPDATE SET name = excluded.name, description = excluded.description",
        [(area.slug, area.name, area.description) for area in content.areas],
    )
    conn.executemany(
        "INSERT INTO competencies (area_id, slug, name, description) "
        "VALUES ((SELECT id FROM areas WHERE slug = ?), ?, ?, ?) "
        "ON CONFLICT (slug) DO UPDATE SET area_id = excluded.area_id, name = excluded.name, "
        "description = excluded.description",
        [(c.area_slug, c.slug, c.name, c.description) for c in content.competencies],
    )


def _upsert_tracks_and_modules(conn: sqlite3.Connection, content: ContentDefinition) -> None:
    conn.executemany(
        "INSERT INTO tracks (slug, name, description) VALUES (?, ?, ?) "
        "ON CONFLICT (slug) DO UPDATE SET name = excluded.name, description = excluded.description",
        [(track.slug, track.name, track.description) for track in content.tracks],
    )
    conn.executemany(
        "INSERT INTO modules (track_id, slug, title, summary, content_path, position) "
        "VALUES ((SELECT id FROM tracks WHERE slug = ?), ?, ?, ?, ?, ?) "
        "ON CONFLICT (track_id, slug) DO UPDATE SET title = excluded.title, "
        "summary = excluded.summary, content_path = excluded.content_path, "
        "position = excluded.position",
        [
            (m.track_slug, m.slug, m.title, m.summary, m.content_path, position)
            for track in content.tracks
            for position, m in enumerate(track.modules, start=1)
        ],
    )


def _module_ids_by_key(conn: sqlite3.Connection) -> dict[str, int]:
    rows = conn.execute(
        "SELECT modules.id, tracks.slug AS track_slug, modules.slug AS module_slug "
        "FROM modules JOIN tracks ON tracks.id = modules.track_id"
    )
    return {module_key(row["track_slug"], row["module_slug"]): row["id"] for row in rows}


def _replace_module_links(
    conn: sqlite3.Connection, content: ContentDefinition, ids_by_key: dict[str, int]
) -> None:
    synced_ids = [(ids_by_key[module.key],) for module in content.modules]
    conn.executemany("DELETE FROM module_prerequisites WHERE module_id = ?", synced_ids)
    conn.executemany("DELETE FROM module_competencies WHERE module_id = ?", synced_ids)
    conn.executemany(
        "INSERT INTO module_prerequisites (module_id, prerequisite_id) VALUES (?, ?)",
        [
            (ids_by_key[module.key], ids_by_key[prerequisite])
            for module in content.modules
            for prerequisite in module.requires
        ],
    )
    conn.executemany(
        "INSERT INTO module_competencies (module_id, competency_id) "
        "VALUES (?, (SELECT id FROM competencies WHERE slug = ?))",
        [
            (ids_by_key[module.key], competency_slug)
            for module in content.modules
            for competency_slug in module.competencies
        ],
    )


def sync_content(conn: sqlite3.Connection, content: ContentDefinition) -> SyncReport:
    with conn:
        _upsert_catalog(conn, content)
        _upsert_tracks_and_modules(conn, content)
        ids_by_key = _module_ids_by_key(conn)
        _replace_module_links(conn, content, ids_by_key)
        retired_questions = sync_questions(conn, content.questions)

    defined_keys = {module.key for module in content.modules}
    orphans = tuple(sorted(key for key in ids_by_key if key not in defined_keys))
    return SyncReport(
        areas=len(content.areas),
        competencies=len(content.competencies),
        tracks=len(content.tracks),
        modules=len(content.modules),
        orphan_modules=orphans,
        questions=len(content.questions),
        retired_questions=retired_questions,
    )
