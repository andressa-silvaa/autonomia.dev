from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from hone.config import PROJECT_ROOT
from hone.engines.content import ContentError, load_content, sync_content
from tests.content_builder import SAMPLE_TRACK, write_content

REAL_CONTENT_DIR = PROJECT_ROOT / "data"


def _problems_for(root: Path) -> list[str]:
    with pytest.raises(ContentError) as caught:
        load_content(root)
    return caught.value.problems


def test_real_repository_content_is_valid() -> None:
    content = load_content(REAL_CONTENT_DIR)
    assert any(track.slug == "cs-fundamentals" for track in content.tracks)
    assert len(content.modules) >= 8


def test_sample_content_loads_with_qualified_prerequisites(content_dir: Path) -> None:
    content = load_content(content_dir)
    third = next(module for module in content.modules if module.slug == "third")
    assert third.requires == ("sample/first", "sample/second")
    assert third.content_path == "sample/03-third.md"


def test_unknown_prerequisite_is_reported(tmp_path: Path) -> None:
    track = SAMPLE_TRACK.replace('requires = ["first"]', 'requires = ["ghost"]')
    problems = _problems_for(write_content(tmp_path, tracks={"sample": track}))
    assert any("unknown module 'sample/ghost'" in problem for problem in problems)


def test_prerequisite_cycle_is_reported(tmp_path: Path) -> None:
    track = SAMPLE_TRACK.replace(
        'content = "01-first.md"', 'content = "01-first.md"\nrequires = ["third"]'
    )
    problems = _problems_for(write_content(tmp_path, tracks={"sample": track}))
    assert any("prerequisite cycle" in problem for problem in problems)


def test_missing_content_file_is_reported(tmp_path: Path) -> None:
    track = SAMPLE_TRACK.replace("02-second.md", "99-missing.md")
    problems = _problems_for(write_content(tmp_path, tracks={"sample": track}))
    assert any("'99-missing.md' not found" in problem for problem in problems)


def test_content_outside_track_folder_is_rejected(tmp_path: Path) -> None:
    track = SAMPLE_TRACK.replace("02-second.md", "../../catalog.toml")
    problems = _problems_for(write_content(tmp_path, tracks={"sample": track}))
    assert any("must stay inside" in problem for problem in problems)


def test_folder_name_must_match_track_slug(tmp_path: Path) -> None:
    problems = _problems_for(write_content(tmp_path, tracks={"other-name": SAMPLE_TRACK}))
    assert any("must match folder name" in problem for problem in problems)


def test_unknown_competency_is_reported(tmp_path: Path) -> None:
    track = SAMPLE_TRACK.replace('competencies = ["basics"]', 'competencies = ["nope"]')
    problems = _problems_for(write_content(tmp_path, tracks={"sample": track}))
    assert any("unknown competency 'nope'" in problem for problem in problems)


def test_invalid_toml_is_reported(tmp_path: Path) -> None:
    problems = _problems_for(write_content(tmp_path, tracks={"sample": "[track\nslug="}))
    assert any("invalid TOML" in problem for problem in problems)


def test_sync_is_idempotent_and_links_prerequisites(
    conn: sqlite3.Connection, content_dir: Path
) -> None:
    content = load_content(content_dir)
    sync_content(conn, content)
    report = sync_content(conn, content)

    assert (report.tracks, report.modules, report.orphan_modules) == (1, 3, ())
    assert conn.execute("SELECT COUNT(*) FROM modules").fetchone()[0] == 3
    assert conn.execute("SELECT COUNT(*) FROM module_prerequisites").fetchone()[0] == 3
    assert conn.execute("SELECT COUNT(*) FROM module_competencies").fetchone()[0] == 2
    assert (report.questions, report.retired_questions) == (3, ())
    assert conn.execute("SELECT COUNT(*) FROM diagnostic_questions").fetchone()[0] == 3


def test_sync_updates_titles_and_reports_orphans(conn: sqlite3.Connection, tmp_path: Path) -> None:
    root = write_content(tmp_path / "v1")
    sync_content(conn, load_content(root))

    trimmed = SAMPLE_TRACK.split('[[modules]]\nslug = "third"')[0].replace(
        "Primeiro", "Primeiro v2"
    )
    report = sync_content(
        conn, load_content(write_content(tmp_path / "v2", tracks={"sample": trimmed}))
    )

    assert report.orphan_modules == ("sample/third",)
    title = conn.execute("SELECT title FROM modules WHERE slug = 'first'").fetchone()[0]
    assert title == "Primeiro v2"
