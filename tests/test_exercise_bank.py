from __future__ import annotations

import sqlite3
from collections import Counter
from pathlib import Path

import pytest

from hone.config import PROJECT_ROOT
from hone.core.models import AnswerFormat
from hone.engines.content import ContentError, load_content, sync_content
from tests.content_builder import SAMPLE_EXERCISES, write_content, write_exercises

REAL_CONTENT_DIR = PROJECT_ROOT / "data"
REAL_EXERCISES_DIR = PROJECT_ROOT / "exercises"


def _problems_for(
    content_root: Path, exercises: dict[str, dict[str, str]], tmp_path: Path
) -> list[str]:
    exercises_root = write_exercises(tmp_path / "exercises-under-test", exercises)
    with pytest.raises(ContentError) as caught:
        load_content(content_root, exercises_root)
    return caught.value.problems


def _with_changed_toml(relative: str, old: str, new: str) -> dict[str, dict[str, str]]:
    changed = {key: dict(files) for key, files in SAMPLE_EXERCISES.items()}
    changed[relative]["exercise.toml"] = changed[relative]["exercise.toml"].replace(old, new)
    return changed


def test_real_exercises_give_every_module_one_required_exercise() -> None:
    content = load_content(REAL_CONTENT_DIR, REAL_EXERCISES_DIR)
    required_per_module = Counter(e.module_key for e in content.exercises if e.required)
    for module in content.modules:
        assert required_per_module[module.key] == 1, module.key


def test_sample_exercises_detect_their_answer_format(
    content_dir: Path, exercises_dir: Path
) -> None:
    exercises = {e.slug: e for e in load_content(content_dir, exercises_dir).exercises}
    assert exercises["pick-right"].answer_format is AnswerFormat.CHOICE
    assert exercises["pick-right"].accepted_answers == ("certa",)
    assert exercises["pick-right"].required
    assert exercises["double-it"].answer_format is AnswerFormat.CODE
    assert exercises["explain-it"].answer_format is AnswerFormat.TEXT
    assert exercises["explain-it"].reference_answer == "Uma resposta de referência."
    assert exercises["double-it"].base_xp == 10
    assert exercises["double-it"].source_path == "sample/first/double-it"


@pytest.mark.parametrize(
    ("relative", "old", "new", "expected_problem"),
    [
        ("first/pick-right", "difficulty = 2", "difficulty = 9", "difficulty must be between"),
        ("first/pick-right", 'kind = "quiz"', 'kind = "poem"', "unknown kind 'poem'"),
        ("first/pick-right", 'grading = "auto"', 'grading = "ollama"', "must use grading = 'auto'"),
        (
            "second/explain-it",
            'grading = "ollama"',
            'grading = "auto"',
            "must use grading = 'ollama'",
        ),
        (
            "second/explain-it",
            'rubric = ["cita o primeiro ponto", "cita o segundo ponto"]',
            "",
            "exactly one answer format",
        ),
        (
            "first/pick-right",
            "answer = 1",
            'answer = 1\nrubric = ["x"]',
            "exactly one answer format",
        ),
        ("first/pick-right", "required = true", 'required = "sim"', "must be true or false"),
    ],
)
def test_invalid_exercises_are_reported(
    content_dir: Path, tmp_path: Path, relative: str, old: str, new: str, expected_problem: str
) -> None:
    problems = _problems_for(content_dir, _with_changed_toml(relative, old, new), tmp_path)
    assert any(expected_problem in problem for problem in problems), problems


def test_code_exercise_needs_a_starter(content_dir: Path, tmp_path: Path) -> None:
    broken = {key: dict(files) for key, files in SAMPLE_EXERCISES.items()}
    del broken["first/double-it"]["starter.py"]
    problems = _problems_for(content_dir, broken, tmp_path)
    assert any("need a starter.py" in problem for problem in problems)


def test_exercise_must_live_in_a_known_module(content_dir: Path, tmp_path: Path) -> None:
    misplaced = {"ghost/pick-right": SAMPLE_EXERCISES["first/pick-right"]}
    problems = _problems_for(content_dir, misplaced, tmp_path)
    assert any("unknown module 'sample/ghost'" in problem for problem in problems)


def test_exercise_slugs_are_unique_across_modules(content_dir: Path, tmp_path: Path) -> None:
    duplicated = dict(SAMPLE_EXERCISES)
    duplicated["second/pick-right"] = SAMPLE_EXERCISES["first/pick-right"]
    problems = _problems_for(content_dir, duplicated, tmp_path)
    assert any("duplicate exercise slug 'pick-right'" in problem for problem in problems)


def test_sync_retires_removed_exercises_and_frees_the_module(
    conn: sqlite3.Connection, tmp_path: Path, user_id: int
) -> None:
    content_root = write_content(tmp_path / "content")
    sync_content(conn, load_content(content_root, write_exercises(tmp_path / "v1")))
    trimmed = {key: files for key, files in SAMPLE_EXERCISES.items() if key != "first/pick-right"}
    report = sync_content(
        conn, load_content(content_root, write_exercises(tmp_path / "v2", trimmed))
    )

    assert report.retired_exercises == ("pick-right",)
    row = conn.execute(
        "SELECT retired, required FROM exercises WHERE slug = 'pick-right'"
    ).fetchone()
    assert (row["retired"], row["required"]) == (1, 0)
