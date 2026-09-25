from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from hone.core.models import GradingMethod
from hone.engines import submissions
from hone.engines.grading import CriterionResult, RubricResult
from tests.content_builder import PASSING_DOUBLE


def _unlock_second_module(client: TestClient) -> None:
    client.post("/api/exercises/pick-right/submissions", json={"answer": "certa"})
    assert client.post("/api/tracks/sample/modules/first/complete").status_code == 200


def test_exercise_detail_starts_from_the_starter(client: TestClient) -> None:
    detail = client.get("/api/exercises/double-it").json()
    assert detail["answer_format"] == "code"
    assert "raise NotImplementedError" in detail["draft"]
    assert "<code>double(n)</code>" in detail["statement_html"]
    assert detail["module_open"] and detail["attempts"] == []
    assert client.get("/api/exercises/ghost").status_code == 404


def test_drafts_are_saved_to_the_workspace(client: TestClient, workspace_dir: Path) -> None:
    client.put("/api/exercises/double-it/draft", json={"content": "def double(n):\n    pass\n"})
    saved = workspace_dir / "sample" / "first" / "double-it" / "solution.py"
    assert saved.read_text(encoding="utf-8") == "def double(n):\n    pass\n"
    assert "pass" in client.get("/api/exercises/double-it").json()["draft"]
    assert client.get("/api/exercises/double-it").json()["status"] == "started"


def test_hints_from_the_browser(client: TestClient) -> None:
    hint = client.post("/api/exercises/pick-right/hints").json()
    assert (hint["hint"], hint["number"], hint["total"]) == ("primeira dica", 1, 2)
    client.post("/api/exercises/pick-right/hints")
    assert client.post("/api/exercises/pick-right/hints").status_code == 409
    assert client.get("/api/exercises/pick-right").json()["hints_revealed"] == [
        "primeira dica",
        "segunda dica",
    ]


def test_choice_exercise_does_not_reveal_the_answer(client: TestClient) -> None:
    wrong = client.post("/api/exercises/pick-right/submissions", json={"answer": "errada"}).json()
    assert (wrong["passed"], wrong["answer_correct"]) == (False, False)
    assert "certa" not in str(wrong)

    right = client.post(
        "/api/exercises/pick-right/submissions", json={"answer": "certa", "used_ai": True}
    ).json()
    assert right["passed"] and right["first_pass"]
    assert right["xp_message"] == "+5 XP de competência · +2 XP de atividade"
    assert right["promotions"][0]["after_label"] == "reconhece"
    assert right["module_ready_message"].startswith("Os exercícios obrigatórios")

    attempts = client.get("/api/exercises/pick-right").json()["attempts"]
    assert [a["passed"] for a in attempts] == [False, True]
    assert attempts[1]["used_ai"]


def test_code_exercise_runs_the_real_tests(client: TestClient) -> None:
    failing = client.post(
        "/api/exercises/double-it/submissions",
        json={"content": "def double(n):\n    return n\n"},
    ).json()
    assert failing["passed"] is False
    assert (failing["test_run"]["passed"], failing["test_run"]["total"]) == (0, 1)
    assert failing["test_run"]["failures"][0]["name"] == "test_doubles"

    passing = client.post(
        "/api/exercises/double-it/submissions", json={"content": PASSING_DOUBLE}
    ).json()
    assert passing["passed"] and passing["test_run"]["passed"] == 1
    assert passing["promotions"][0]["after"] == "can_apply"


def test_text_exercise_falls_back_to_self_assessment_without_ollama(client: TestClient) -> None:
    _unlock_second_module(client)
    pending = client.post(
        "/api/exercises/explain-it/submissions", json={"content": "# Sua resposta\n\nPonto um."}
    ).json()
    assert pending["passed"] is None
    assert "Ollama não respondeu" in pending["self_assessment"]["message"]
    assert pending["self_assessment"]["rubric"] == ["cita o primeiro ponto", "cita o segundo ponto"]
    assert "referência" in pending["self_assessment"]["reference_html"]
    assert client.get("/api/exercises/explain-it").json()["attempts"] == []

    graded = client.post(
        "/api/exercises/explain-it/self-assessments", json={"met": [True, True]}
    ).json()
    assert graded["passed"] and graded["rubric"]["graded_by_label"] == "autoavaliação"
    assert graded["promotions"][0]["after_label"] == "reconhece"

    bad = client.post("/api/exercises/explain-it/self-assessments", json={"met": [True]})
    assert bad.status_code == 422


def test_self_graded_exercise_always_asks_for_self_assessment(client: TestClient) -> None:
    _unlock_second_module(client)
    pending = client.post(
        "/api/exercises/self-check/submissions", json={"content": "minha resposta"}
    ).json()
    assert pending["self_assessment"]["message"].startswith("Este é de autoavaliação")
    graded = client.post(
        "/api/exercises/self-check/self-assessments", json={"met": [True, False, False]}
    ).json()
    assert graded["passed"] is False


def test_text_exercise_graded_by_ollama(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    _unlock_second_module(client)

    def fake_rubric(settings, exercise, answer):
        return RubricResult(
            (
                CriterionResult("cita o primeiro ponto", True, "certo"),
                CriterionResult("cita o segundo ponto", True, ""),
            ),
            "Boa explicação.",
            GradingMethod.LOCAL_AI,
        )

    monkeypatch.setattr(submissions, "_ollama_rubric", fake_rubric)
    result = client.post(
        "/api/exercises/explain-it/submissions", json={"content": "Os dois pontos."}
    ).json()
    assert result["passed"] and result["rubric"]["graded_by_label"] == "Ollama"
    assert result["rubric"]["feedback"] == "Boa explicação."
    assert result["self_assessment"] is None


def test_exercises_of_locked_modules_are_refused(client: TestClient) -> None:
    response = client.post("/api/exercises/self-check/submissions", json={"content": "x"})
    assert response.status_code == 409
    assert client.get("/api/exercises/self-check").json()["module_open"] is False


def test_empty_written_answer_is_refused(client: TestClient) -> None:
    _unlock_second_module(client)
    response = client.post(
        "/api/exercises/self-check/submissions", json={"content": "# Sua resposta\n\n"}
    )
    assert response.status_code == 422
    assert "em branco" in response.json()["challenge"]["problem"]


def test_stats_and_overview_xp(client: TestClient) -> None:
    client.post("/api/exercises/pick-right/submissions", json={"answer": "certa"})
    stats = client.get("/api/stats").json()
    assert stats["xp"] == {"competency": 5, "activity": 2}
    assert stats["exercises_passed"] == 1
    basics = next(item for item in stats["competencies"] if item["name"] == "Básico")
    assert (basics["exercises_passed"], basics["exercises_total"]) == (1, 2)
    assert client.get("/api/overview").json()["xp"] == {"competency": 5, "activity": 2}
