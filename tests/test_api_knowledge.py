from __future__ import annotations

from fastapi.testclient import TestClient

ANSWERS = {
    "basics-concept": ("certa", "sure"),
    "basics-code": ("2", "sure"),
    "advanced-concept": ("", "dont_know"),
}


def _answer(client: TestClient, question: dict, answer: str, confidence: str) -> dict:
    response = client.post(
        "/api/diagnostic/answers",
        json={"question_id": question["id"], "answer": answer, "confidence": confidence},
    )
    assert response.status_code == 200, response.text
    return response.json()


def _slug_by_prompt(prompt_html: str) -> str:
    if "certa" in prompt_html:
        return "basics-concept"
    if "1 + 1" in prompt_html:
        return "basics-code"
    return "advanced-concept"


def test_full_diagnostic_from_the_browser(client: TestClient) -> None:
    assert client.get("/api/diagnostic").json() is None
    assert client.get("/api/diagnostic/report").status_code == 404

    state = client.post("/api/diagnostic").json()
    assert (state["answered"], state["total"]) == (0, 3)
    first = state["question"]
    assert first["is_choice"] and first["options"] == ["certa", "errada"]
    assert "Qual é a certa?" in first["prompt_html"]

    feedback = None
    question = first
    while question is not None:
        answer, confidence = ANSWERS[_slug_by_prompt(question["prompt_html"])]
        feedback = _answer(client, question, answer, confidence)
        question = feedback["next_state"]["question"] if feedback["next_state"] else None

    assert feedback is not None and feedback["report"] is not None
    assert feedback["correct_answer"] == "não"
    results = {r["competency_name"]: r for r in feedback["report"]["results"]}
    assert results["Básico"]["assessed_label"] == "consegue aplicar"
    assert results["Avançado"]["assessed"] == "unknown"
    assert client.get("/api/diagnostic").json() is None
    assert client.get("/api/diagnostic/report").json()["message"].startswith("Diagnóstico feito")
    assert client.get("/api/knowledge-map").json()["last_diagnostic_at"] is not None


def test_a_stale_question_is_refused(client: TestClient) -> None:
    question = client.post("/api/diagnostic").json()["question"]
    _answer(client, question, "certa", "guess")
    stale = client.post(
        "/api/diagnostic/answers",
        json={"question_id": question["id"], "answer": "certa", "confidence": "sure"},
    )
    assert stale.status_code == 409
    assert "já foi respondida" in stale.json()["challenge"]["problem"]


def test_answers_need_a_diagnostic_in_progress(client: TestClient) -> None:
    response = client.post(
        "/api/diagnostic/answers", json={"question_id": 1, "answer": "x", "confidence": "sure"}
    )
    assert response.status_code == 409
    assert "aba Mapa" in response.json()["challenge"]["next_step"]


def test_goal_is_set_and_removed_from_the_browser(client: TestClient) -> None:
    assert client.get("/api/learning-path").json()["goal"] is None

    result = client.put("/api/goal", json={"module_key": "third"}).json()
    assert result["message"] == "Objetivo definido: “Terceiro”. Agora cada módulo tem um porquê."
    assert [step["module"]["slug"] for step in result["path"]["steps"]] == [
        "first",
        "second",
        "third",
    ]
    assert client.get("/api/overview").json()["goal"]["slug"] == "third"

    cleared = client.delete("/api/goal").json()
    assert cleared["goal"] is None
    assert client.put("/api/goal", json={"module_key": "ghost"}).status_code == 404


def test_map_and_levels(client: TestClient) -> None:
    knowledge_map = client.get("/api/knowledge-map").json()
    assert [c["slug"] for c in knowledge_map["areas"][0]["competencies"]] == ["basics", "advanced"]
    levels = client.get("/api/module-levels").json()
    assert [[module["slug"] for module in level] for level in levels] == [
        ["first"],
        ["second"],
        ["third"],
    ]
