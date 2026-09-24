from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from typer.testing import CliRunner

from hone.api.app import app as api_app
from hone.cli.app import app as cli_app

runner = CliRunner()

ALL_ANSWERS = "1\ns\n2\n\n0\n"


@pytest.fixture
def ready(db_path: Path, content_dir: Path) -> None:
    assert runner.invoke(cli_app, ["db", "init"]).exit_code == 0
    result = runner.invoke(cli_app, ["content", "sync"])
    assert result.exit_code == 0, result.output
    assert "3" in result.output


def _run(*args: str, answers: str | None = None) -> str:
    result = runner.invoke(cli_app, list(args), input=answers)
    assert result.exit_code == 0, result.output
    return " ".join(result.output.split())


def _run_expecting_challenge(*args: str) -> str:
    result = runner.invoke(cli_app, list(args))
    assert result.exit_code == 1, result.output
    assert "Desafio" in result.output
    return result.output


def test_diagnostic_from_the_terminal_fills_the_map(ready: None) -> None:
    _run_expecting_challenge("diagnostic", "result")
    assert "hone diagnostic start" in _run("map")

    output = _run("diagnostic", "start", answers=ALL_ANSWERS)
    assert "3 perguntas" in output
    assert "Isso! Essa você sabia." in output
    assert "Dizer “não sei” é dado honesto" in output
    assert "Resposta: não" in output
    assert "Diagnóstico feito: 1 de 2" in output

    map_output = _run("map")
    assert "consegue aplicar" in map_output
    assert "desconhecido" in map_output
    assert "Diagnóstico feito" in _run("diagnostic", "result")


def test_diagnostic_can_pause_and_resume(ready: None) -> None:
    assert "Pausado" in _run("diagnostic", "start", answers="9\n1\ns\npausar\n")
    output = _run("diagnostic", "start", answers="2\n\n0\n")
    assert "Retomando de onde você parou: 1 de 3" in output
    assert "Diagnóstico feito" in output


def test_invalid_choice_asks_again(ready: None) -> None:
    output = _run("diagnostic", "start", answers="9\n" + ALL_ANSWERS)
    assert "Digite um número de 0 a 2" in output


def test_goal_path_and_gaps_from_the_terminal(ready: None) -> None:
    _run_expecting_challenge("path")
    assert "Nenhum objetivo definido" in _run("goal")

    output = _run("goal", "third")
    assert "Objetivo definido: “Terceiro”" in output
    assert "Primeiro" in output and "Segundo" in output
    assert "hone read sample/first" in output

    _run("diagnostic", "start", answers=ALL_ANSWERS)
    path_output = _run("path")
    assert "o diagnóstico diz que você já aplica isto" in path_output
    assert "hone done sample/first" in path_output
    assert "rumo a “Terceiro”" in _run("today")

    gaps_output = _run("gaps")
    assert "Avançado" in gaps_output
    assert "Básico" not in gaps_output

    assert "Objetivo removido" in _run("goal", "--clear")
    assert "Sem objetivo" in _run("gaps")


def test_path_accepts_an_explicit_module(ready: None) -> None:
    output = _run("path", "second")
    assert "caminho até “Segundo”" in output
    assert "Terceiro" not in output


def test_knowledge_endpoints(ready: None) -> None:
    client = TestClient(api_app)

    empty_map = client.get("/api/knowledge-map").json()
    assert empty_map["last_diagnostic_at"] is None
    assert empty_map["max_mastery_rank"] == 7
    assert [c["slug"] for c in empty_map["areas"][0]["competencies"]] == ["basics", "advanced"]

    no_goal = client.get("/api/learning-path").json()
    assert (no_goal["goal"], no_goal["steps"], no_goal["gaps"]) == (None, [], [])

    _run("diagnostic", "start", answers="pausar\n")
    assert client.get("/api/knowledge-map").json()["open_diagnostic"] == {"answered": 0, "total": 3}
    _run("diagnostic", "start", answers=ALL_ANSWERS)
    _run("goal", "third")

    knowledge_map = client.get("/api/knowledge-map").json()
    basics = knowledge_map["areas"][0]["competencies"][0]
    assert (basics["mastery"], basics["mastery_label"], basics["is_solid"]) == (
        "can_apply",
        "consegue aplicar",
        True,
    )
    assert knowledge_map["last_diagnostic_at"] is not None
    assert knowledge_map["open_diagnostic"] is None

    path = client.get("/api/learning-path").json()
    assert path["goal"]["slug"] == "third"
    assert [(s["module"]["slug"], s["likely_known"]) for s in path["steps"]] == [
        ("first", True),
        ("second", False),
        ("third", False),
    ]
    assert [gap["slug"] for gap in path["gaps"]] == ["advanced"]

    levels = client.get("/api/module-levels").json()
    assert [[module["slug"] for module in level] for level in levels] == [
        ["first"],
        ["second"],
        ["third"],
    ]
    assert client.get("/api/overview").json()["goal"]["slug"] == "third"
