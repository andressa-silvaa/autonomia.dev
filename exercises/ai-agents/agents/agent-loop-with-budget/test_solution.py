from dataclasses import dataclass, field

from solution import run_agent


@dataclass
class FakeResponse:
    stop_reason: str
    tokens: int
    tool_calls: list = field(default_factory=list)


class FakeClient:
    def __init__(self, responses):
        self.responses = list(responses)
        self.sent = 0

    def send(self, messages):
        self.sent += 1
        return self.responses.pop(0)

    def run_tools(self, tool_calls):
        return {"role": "user", "content": "resultado"}


def test_stops_when_model_is_done():
    client = FakeClient([FakeResponse("end_turn", 100)])
    assert run_agent(client, [], 5, 10_000) == {"reason": "done", "turns": 1, "tokens": 100}


def test_runs_tools_until_done():
    client = FakeClient(
        [
            FakeResponse("tool_use", 100, [{"id": "1"}]),
            FakeResponse("tool_use", 100, [{"id": "2"}]),
            FakeResponse("end_turn", 50),
        ]
    )
    assert run_agent(client, [], 10, 10_000) == {"reason": "done", "turns": 3, "tokens": 250}


def test_stops_on_max_turns():
    client = FakeClient([FakeResponse("tool_use", 10, [{"id": "1"}]) for _ in range(5)])
    result = run_agent(client, [], 3, 10_000)
    assert result["reason"] == "max_turns"
    assert result["turns"] == 3
    assert client.sent == 3


def test_stops_on_budget():
    client = FakeClient([FakeResponse("tool_use", 400, [{"id": "1"}]) for _ in range(5)])
    result = run_agent(client, [], 10, 1000)
    assert result["reason"] == "budget"
    assert result["tokens"] == 1200
    assert result["turns"] == 3


def test_done_wins_over_limits_on_the_last_turn():
    client = FakeClient(
        [
            FakeResponse("tool_use", 500, [{"id": "1"}]),
            FakeResponse("end_turn", 600),
        ]
    )
    result = run_agent(client, [], 2, 1000)
    assert result["reason"] == "done"


def test_history_grows_with_tool_results():
    client = FakeClient(
        [
            FakeResponse("tool_use", 10, [{"id": "1"}]),
            FakeResponse("end_turn", 10),
        ]
    )
    messages = [{"role": "user", "content": "comece"}]
    run_agent(client, messages, 5, 10_000)
    assert len(messages) == 1
