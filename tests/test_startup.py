from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest
from typer.testing import CliRunner

from hone import cli
from hone.config import load_settings
from hone.core.db import latest_version
from hone.startup import prepare_system
from tests.content_builder import SAMPLE_TRACK, write_content

runner = CliRunner()


def test_first_start_creates_everything(
    db_path: Path, content_dir: Path, exercises_dir: Path
) -> None:
    report = prepare_system(load_settings())
    assert report.first_run and report.user_name == "Tester"
    assert len(report.applied_migrations) == latest_version()
    assert (report.sync.modules, report.sync.questions, report.sync.exercises) == (3, 3, 4)

    with sqlite3.connect(db_path) as conn:
        assert conn.execute("SELECT COUNT(*) FROM exercises").fetchone()[0] == 4


def test_next_starts_keep_the_data(db_path: Path, content_dir: Path, exercises_dir: Path) -> None:
    prepare_system(load_settings())
    again = prepare_system(load_settings())
    assert not again.first_run
    assert again.applied_migrations == ()


def test_version_flag() -> None:
    result = runner.invoke(cli.app, ["--version"])
    assert result.exit_code == 0
    assert "hone 0.1.0" in result.output


def test_invalid_content_stops_with_a_challenge(
    db_path: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    broken = SAMPLE_TRACK.replace('requires = ["first"]', 'requires = ["ghost"]')
    root = write_content(tmp_path / "broken", tracks={"sample": broken})
    monkeypatch.setenv("HONE_CONTENT_DIR", str(root))
    monkeypatch.setattr(cli, "_is_already_running", lambda settings: False)

    result = runner.invoke(cli.app, [])
    assert result.exit_code == 1
    assert "Desafio" in result.output
    assert "sample/ghost" in result.output


def test_second_launch_just_opens_the_browser(monkeypatch: pytest.MonkeyPatch) -> None:
    opened = []
    monkeypatch.setattr(cli, "_is_already_running", lambda settings: True)
    monkeypatch.setattr(cli.webbrowser, "open", opened.append)

    result = runner.invoke(cli.app, [])
    assert result.exit_code == 0
    assert "já estava aberto" in result.output
    assert opened == ["http://127.0.0.1:8000"]
