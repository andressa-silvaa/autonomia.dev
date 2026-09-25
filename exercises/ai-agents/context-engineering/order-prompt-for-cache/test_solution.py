from solution import build_request

MANUAL = "Manual longo e estável."
TOOLS = [{"name": "search"}, {"name": "add_note"}, {"name": "list_users"}]


def _request(question="Como faço X?", now="2026-09-25 10:00"):
    return build_request(MANUAL, TOOLS, question, now)


def test_tools_are_sorted_by_name():
    assert [tool["name"] for tool in _request()["tools"]] == ["add_note", "list_users", "search"]


def test_stable_block_comes_first_and_is_cached():
    system = _request()["system"]
    assert system[0]["text"] == MANUAL
    assert system[0]["cache_control"] == {"type": "ephemeral"}


def test_volatile_block_comes_last_and_is_not_cached():
    system = _request()["system"]
    assert system[-1]["text"] == "Agora: 2026-09-25 10:00"
    assert "cache_control" not in system[-1]


def test_question_goes_into_messages():
    messages = _request(question="Quanto custa?")["messages"]
    assert messages[0]["role"] == "user"
    assert "Quanto custa?" in str(messages[0]["content"])


def test_cached_prefix_is_identical_across_calls():
    first = _request(question="A", now="10:00")
    second = _request(question="B", now="11:00")
    assert first["tools"] == second["tools"]
    assert first["system"][0] == second["system"][0]
