from __future__ import annotations

from pathlib import Path

import pytest

from hone.core.models import GradingMethod
from hone.engines import grading, ollama
from hone.engines.grading import (
    RubricGradingError,
    grade_with_ollama,
    matches_accepted_answer,
    run_python_tests,
    self_assessed_result,
)
from hone.engines.ollama import OllamaModelMissingError, OllamaUnavailableError, ensure_model

TESTS_SOURCE = """from solution import double


def test_two():
    assert double(2) == 4


def test_zero():
    assert double(0) == 0
"""
RUBRIC = ("ponto um", "ponto dois", "ponto três")
TIMEOUT_SECONDS = 20
SHORT_TIMEOUT_SECONDS = 3


def _run(tmp_path: Path, solution: str, timeout: int = TIMEOUT_SECONDS):
    solution_path = tmp_path / "solution.py"
    tests_path = tmp_path / "test_solution.py"
    solution_path.write_text(solution, encoding="utf-8")
    tests_path.write_text(TESTS_SOURCE, encoding="utf-8")
    return run_python_tests(solution_path, tests_path, timeout)


def test_passing_solution(tmp_path: Path) -> None:
    result = _run(tmp_path, "def double(n):\n    return n * 2\n")
    assert (result.passed, result.total, result.is_passing, result.score) == (2, 2, True, 1.0)


def test_partial_solution_reports_the_failure(tmp_path: Path) -> None:
    result = _run(tmp_path, "def double(n):\n    return 4\n")
    assert (result.passed, result.total, result.is_passing) == (1, 2, False)
    assert result.failures[0].name == "test_zero"
    assert "assert 4 == 0" in result.failures[0].message


def test_broken_solution_fails_without_crashing(tmp_path: Path) -> None:
    result = _run(tmp_path, "def double(n)\n    return n\n")
    assert not result.is_passing
    assert result.passed == 0


def test_infinite_loop_times_out(tmp_path: Path) -> None:
    result = _run(
        tmp_path, "def double(n):\n    while True:\n        pass\n", SHORT_TIMEOUT_SECONDS
    )
    assert result.timed_out
    assert not result.is_passing


def test_answer_matching_ignores_spaces_and_case() -> None:
    assert matches_accepted_answer(" O(N^2) ", ["O(n^2)"])
    assert not matches_accepted_answer("", ["O(n^2)"])


def test_rubric_pass_threshold() -> None:
    assert self_assessed_result(RUBRIC, [True, True, True]).is_passing
    assert not self_assessed_result(RUBRIC, [True, False, False]).is_passing
    assert (
        self_assessed_result(RUBRIC, [True, True, False]).graded_by is GradingMethod.SELF_ASSESSMENT
    )


def test_ollama_grading_maps_each_criterion(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_chat(*args, **kwargs):
        return {
            "criteria": [
                {"met": True, "comment": "boa"},
                {"met": True, "comment": ""},
                {"met": False, "comment": "faltou"},
            ],
            "feedback": "Quase lá.",
        }

    monkeypatch.setattr(grading, "chat_json", fake_chat)
    result = grade_with_ollama("http://x", "model", "enunciado", RUBRIC, "", "resposta")
    assert [item.met for item in result.criteria] == [True, True, False]
    assert result.criteria[2].comment == "faltou"
    assert result.graded_by is GradingMethod.LOCAL_AI
    assert result.is_passing


def test_ollama_grading_rejects_incomplete_judgement(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(grading, "chat_json", lambda *a, **k: {"criteria": [], "feedback": ""})
    with pytest.raises(RubricGradingError):
        grade_with_ollama("http://x", "model", "enunciado", RUBRIC, "", "resposta")


def test_unreachable_ollama_is_reported() -> None:
    with pytest.raises(OllamaUnavailableError):
        ensure_model("http://127.0.0.1:9", "qwen2.5-coder:7b")


def test_missing_model_is_reported(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ollama, "installed_models", lambda base_url: ["llama3.2:latest"])
    ensure_model("http://x", "llama3.2")
    with pytest.raises(OllamaModelMissingError):
        ensure_model("http://x", "qwen2.5-coder:7b")
