from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from typer.testing import CliRunner

from formacao.api.app import app as api_app
from formacao.cli.app import app as cli_app

runner = CliRunner()


def test_db_status_without_database_suggests_init(db_path: Path) -> None:
    result = runner.invoke(cli_app, ["db", "status"])
    assert result.exit_code == 1
    assert "formacao db init" in result.output


def test_db_init_then_status(db_path: Path) -> None:
    first = runner.invoke(cli_app, ["db", "init"])
    assert first.exit_code == 0, first.output
    assert "0001" in first.output
    assert "Oi, Tester" in first.output
    assert db_path.exists()

    second = runner.invoke(cli_app, ["db", "init"])
    assert second.exit_code == 0
    assert "já estava em dia" in second.output

    status = runner.invoke(cli_app, ["db", "status"])
    assert status.exit_code == 0
    assert "em dia" in status.output
    assert "users" in status.output


def test_health_reports_database_state(db_path: Path) -> None:
    client = TestClient(api_app)
    assert client.get("/health").json()["status"] == "no_database"

    runner.invoke(cli_app, ["db", "init"])
    body = client.get("/health").json()
    assert body["status"] == "ok"
    assert body["schema_version"] == body["latest_schema"]


def test_version_flag() -> None:
    result = runner.invoke(cli_app, ["--version"])
    assert result.exit_code == 0
    assert "0.1.0" in result.output


def test_unwritable_database_path_becomes_a_challenge(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    blocking_file = tmp_path / "not_a_folder"
    blocking_file.write_text("", encoding="utf-8")
    monkeypatch.setenv("FORMACAO_DB_PATH", str(blocking_file / "db.sqlite"))
    result = runner.invoke(cli_app, ["db", "init"])
    assert result.exit_code == 1
    assert "Desafio" in result.output
