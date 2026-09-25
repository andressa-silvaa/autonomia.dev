from __future__ import annotations

from fastapi.testclient import TestClient

from hone.api.app import app as api_app
from tests.conftest import API_BASE_URL


def _challenge(response) -> dict:
    return response.json()["challenge"]


def test_health_and_dashboard_page(client: TestClient) -> None:
    assert client.get("/health").json()["status"] == "ok"
    assert "autonomia" in client.get("/").text


def test_writes_require_the_dashboard_header(client: TestClient) -> None:
    outsider = TestClient(api_app, base_url=API_BASE_URL)
    response = outsider.post("/api/checkin", json={"intention": "invadir"})
    assert response.status_code == 403
    assert outsider.get("/api/overview").status_code == 200


def test_requests_to_other_hosts_are_refused(client: TestClient) -> None:
    rebinding = TestClient(api_app, base_url="http://evil.example")
    assert rebinding.get("/api/overview").status_code == 400


def test_checkin_from_the_browser(client: TestClient) -> None:
    assert client.get("/api/overview").json()["todays_checkin"] is None

    result = client.post("/api/checkin", json={"intention": "Recursão"}).json()
    assert result["message"] == "Check-in feito. Hoje conta."
    assert result["streak"]["current"] == 1

    again = client.post("/api/checkin", json={"intention": "de novo"})
    assert again.status_code == 409
    assert "já está feito" in _challenge(again)["problem"]
    empty = client.post("/api/checkin", json={"intention": "   "})
    assert empty.status_code == 422


def test_session_start_and_stop(client: TestClient) -> None:
    session = client.post("/api/sessions", json={"module_key": "first"}).json()
    assert session["module_key"] == "sample/first"
    assert client.get("/api/overview").json()["active_session"]["module_title"] == "Primeiro"

    second = client.post("/api/sessions", json={})
    assert second.status_code == 409
    assert "tela Hoje" in _challenge(second)["next_step"]

    stopped = client.post("/api/sessions/stop", json={"notes": "entendi"}).json()
    assert stopped["message"].startswith("Sessão encerrada")
    assert client.post("/api/sessions/stop", json={}).status_code == 409


def test_module_completion_waits_for_required_exercises(client: TestClient) -> None:
    module = client.get("/api/tracks/sample/modules/first").json()
    assert [e["slug"] for e in module["exercises"]] == ["double-it", "pick-right"]
    assert module["pending_required"] == ["Escolha a certa"]

    blocked = client.post("/api/tracks/sample/modules/first/complete")
    assert blocked.status_code == 409
    assert "Escolha a certa" in _challenge(blocked)["problem"]

    client.post("/api/exercises/pick-right/submissions", json={"answer": "certa"})
    done = client.post("/api/tracks/sample/modules/first/complete").json()
    assert done["message"].startswith("Você venceu")
    assert [module["slug"] for module in done["unlocked"]] == ["second"]

    again = client.post("/api/tracks/sample/modules/first/complete").json()
    assert "já estava concluído" in again["message"]


def test_locked_module_cannot_be_completed(client: TestClient) -> None:
    response = client.post("/api/tracks/sample/modules/third/complete")
    assert response.status_code == 409
    assert "trancado" in _challenge(response)["problem"]
