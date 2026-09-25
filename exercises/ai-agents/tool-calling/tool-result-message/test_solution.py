import pytest
from solution import build_tool_results

CALLS = [
    {"id": "toolu_1", "name": "get_price"},
    {"id": "toolu_2", "name": "get_stock"},
]


def test_single_user_message():
    message = build_tool_results(CALLS, {"toolu_1": {"ok": 10}, "toolu_2": {"ok": 3}})
    assert message["role"] == "user"
    assert len(message["content"]) == 2


def test_results_follow_the_call_order():
    message = build_tool_results(CALLS, {"toolu_1": {"ok": "a"}, "toolu_2": {"ok": "b"}})
    assert [block["tool_use_id"] for block in message["content"]] == ["toolu_1", "toolu_2"]


def test_values_become_text():
    message = build_tool_results(CALLS, {"toolu_1": {"ok": 10}, "toolu_2": {"ok": None}})
    assert message["content"][0]["content"] == "10"
    assert message["content"][1]["content"] == "None"


def test_success_blocks_have_no_error_flag():
    message = build_tool_results(CALLS[:1], {"toolu_1": {"ok": 1}})
    assert "is_error" not in message["content"][0]


def test_failed_tool_is_still_returned():
    message = build_tool_results(CALLS, {"toolu_1": {"ok": 1}, "toolu_2": {"error": "timeout"}})
    assert len(message["content"]) == 2
    failed = message["content"][1]
    assert failed["is_error"] is True
    assert failed["content"] == "timeout"


def test_missing_outcome_raises():
    with pytest.raises(KeyError):
        build_tool_results(CALLS, {"toolu_1": {"ok": 1}})
