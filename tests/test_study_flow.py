from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from typer.testing import CliRunner

from formacao.api.app import app as api_app
from formacao.cli.app import app as cli_app

runner = CliRunner()


@pytest.fixture
def ready(db_path: Path, content_dir: Path) -> None:
    assert runner.invoke(cli_app, ["db", "init"]).exit_code == 0
    result = runner.invoke(cli_app, ["content", "sync"])
    assert result.exit_code == 0, result.output


def _run(*args: str) -> str:
    result = runner.invoke(cli_app, list(args))
    assert result.exit_code == 0, result.output
    return result.output


def _run_expecting_challenge(*args: str) -> str:
    result = runner.invoke(cli_app, list(args))
    assert result.exit_code == 1, result.output
    assert "Desafio" in result.output
    return result.output


def test_full_study_day_from_the_terminal(ready: None) -> None:
    assert "pendente" in _run("today")
    assert "Check-in feito" in _run("checkin", "--intention", "Primeiro módulo")
    _run_expecting_challenge("checkin", "--intention", "de novo")

    assert "Conteúdo de" in _run("read", "first")
    assert "Sessão começou" in _run("session", "start", "first")
    _run_expecting_challenge("session", "start")
    assert "Sessão encerrada" in _run("session", "stop", "--notes", "entendi")

    output = _run("done", "first")
    assert "Você venceu" in output
    assert "Segundo" in output

    track_output = _run("track", "sample")
    assert "concluído" in track_output
    assert "trancado" in track_output


def test_checkin_prompts_for_intention_when_missing(ready: None) -> None:
    result = runner.invoke(cli_app, ["checkin"], input="Recursão\n")
    assert result.exit_code == 0, result.output
    assert "O que você vai estudar hoje?" in result.output


def test_locked_module_becomes_a_challenge(ready: None) -> None:
    output = _run_expecting_challenge("read", "third")
    assert "trancado" in output
    assert "Primeiro" in output


def test_completing_whole_track_celebrates(ready: None) -> None:
    for slug in ("first", "second"):
        _run("done", slug)
    assert "completa" in _run("done", "third")


def test_commands_before_init_explain_what_to_do(db_path: Path, content_dir: Path) -> None:
    assert "formacao db init" in _run_expecting_challenge("today")


def test_outdated_schema_asks_for_db_init(db_path: Path, content_dir: Path) -> None:
    _run("db", "init")
    with sqlite3.connect(db_path) as raw:
        raw.execute("PRAGMA user_version = 1")
    assert "atualizar" in _run_expecting_challenge("tracks")


def test_invalid_content_lists_every_problem(ready: None, content_dir: Path) -> None:
    (content_dir / "tracks" / "sample" / "02-second.md").unlink()
    output = _run_expecting_challenge("content", "sync")
    assert "02-second.md" in output


def test_api_serves_overview_track_and_module(ready: None) -> None:
    _run("checkin", "--intention", "API")
    client = TestClient(api_app)

    overview = client.get("/api/overview").json()
    assert overview["user_name"] == "Tester"
    assert overview["streak"]["current"] == 1
    assert overview["todays_checkin"]["intention"] == "API"
    assert len(overview["study_minutes"]) == 14
    assert [module["slug"] for module in overview["next_modules"]] == ["first"]

    track = client.get("/api/tracks/sample").json()
    assert [module["status"] for module in track["modules"]] == ["available", "locked", "locked"]

    module = client.get("/api/tracks/sample/modules/first").json()
    assert "<strong>01-first.md</strong>" in module["content_html"]

    locked = client.get("/api/tracks/sample/modules/third").json()
    assert locked["content_html"] == ""
    assert locked["missing_prerequisites"][0]["title"] == "Primeiro"


def test_api_errors_come_back_as_challenges(ready: None) -> None:
    client = TestClient(api_app)
    missing_track = client.get("/api/tracks/nope")
    assert missing_track.status_code == 404

    missing_module = client.get("/api/tracks/sample/modules/nope")
    assert missing_module.status_code == 404
    assert "não achei" in missing_module.json()["challenge"]["problem"]
    assert "[accent]" not in missing_module.json()["challenge"]["next_step"]


def test_api_without_database_returns_challenge(db_path: Path) -> None:
    response = TestClient(api_app).get("/api/overview")
    assert response.status_code == 503
    assert "formacao db init" in response.json()["challenge"]["next_step"]


def test_dashboard_and_theme_are_served(ready: None) -> None:
    client = TestClient(api_app)
    assert "formação" in client.get("/").text
    tokens = client.get("/theme/tokens.css")
    assert tokens.headers["content-type"].startswith("text/css")
    assert "--accent:" in tokens.text
    assert 'data-theme="dark"' in tokens.text
    assert client.get("/static/app.js").status_code == 200
