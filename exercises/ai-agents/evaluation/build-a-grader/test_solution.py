import pytest
from solution import evaluate

CASES = [("2+2", "4"), ("3+3", "6")]


def test_perfect_system():
    result = evaluate(lambda text: str(eval(text)), CASES, 3)
    assert result["pass_rate"] == 1.0
    assert result["per_case"] == [1.0, 1.0]
    assert result["unstable"] == []
    assert result["runs"] == 6


def test_broken_system():
    result = evaluate(lambda text: "erro", CASES, 2)
    assert result["pass_rate"] == 0.0
    assert result["per_case"] == [0.0, 0.0]
    assert result["unstable"] == []


def test_unstable_case_is_detected():
    calls = {"n": 0}

    def flaky(text):
        calls["n"] += 1
        return "4" if calls["n"] % 2 else "errado"

    result = evaluate(flaky, [("2+2", "4")], 4)
    assert result["unstable"] == [0]
    assert result["per_case"][0] == 0.5


def test_partially_correct_system():
    result = evaluate(lambda text: "4", CASES, 2)
    assert result["pass_rate"] == 0.5
    assert result["per_case"] == [1.0, 0.0]
    assert result["unstable"] == []


def test_empty_cases():
    result = evaluate(lambda text: text, [], 3)
    assert result == {"pass_rate": 0.0, "per_case": [], "unstable": [], "runs": 0}


def test_invalid_repetitions():
    with pytest.raises(ValueError):
        evaluate(lambda text: text, CASES, 0)
