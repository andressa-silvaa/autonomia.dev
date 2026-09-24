from __future__ import annotations

import json
import sqlite3
from collections import Counter
from pathlib import Path

import pytest

from hone.config import PROJECT_ROOT
from hone.core.models import QuestionKind
from hone.engines.content import ContentError, load_content, sync_content
from tests.content_builder import SAMPLE_DIAGNOSTICS, write_content

REAL_CONTENT_DIR = PROJECT_ROOT / "data"
MIN_QUESTIONS_PER_COMPETENCY = 3


def _problems_for(root: Path) -> list[str]:
    with pytest.raises(ContentError) as caught:
        load_content(root)
    return caught.value.problems


def test_real_diagnostic_covers_every_linked_competency_with_code_questions() -> None:
    content = load_content(REAL_CONTENT_DIR)
    linked = {slug for module in content.modules for slug in module.competencies}
    per_competency = Counter(question.competency_slug for question in content.questions)
    for competency in linked:
        assert per_competency[competency] >= MIN_QUESTIONS_PER_COMPETENCY, competency
        assert any(
            question.kind is not None and question.kind.proves_application
            for question in content.questions
            if question.competency_slug == competency
        ), competency


def test_choice_answer_becomes_the_accepted_option_text(content_dir: Path) -> None:
    questions = {question.slug: question for question in load_content(content_dir).questions}
    assert questions["basics-concept"].accepted_answers == ("certa",)
    assert questions["basics-code"].options == ()
    assert questions["basics-code"].accepted_answers == ("2",)
    assert questions["advanced-concept"].kind is QuestionKind.CONCEPT


def test_content_without_diagnostics_folder_still_loads(tmp_path: Path) -> None:
    assert load_content(write_content(tmp_path, diagnostics=None)).questions == ()


@pytest.mark.parametrize(
    ("change", "expected_problem"),
    [
        (('competency = "advanced"', 'competency = "ghost"'), "unknown competency 'ghost'"),
        (("answer = 2", "answer = 3"), "answer must be between 1 and 2"),
        (('kind = "code_reading"', 'kind = "poetry"'), "unknown kind 'poetry'"),
        (('accept = ["2"]', "accept = []"), "needs a non-empty 'accept' list"),
        (('options = ["sim", "não"]', 'options = ["sim"]'), "at least 2 options"),
        (('options = ["sim", "não"]', 'options = ["sim", "sim"]'), "must be different"),
        (('accept = ["2"]', 'accept = ["2"]\noptions = ["2", "3"]'), "not both"),
        (('slug = "advanced-concept"', 'slug = "basics-concept"'), "duplicate question slug"),
    ],
)
def test_invalid_questions_are_reported(
    tmp_path: Path, change: tuple[str, str], expected_problem: str
) -> None:
    old, new = change
    diagnostics = SAMPLE_DIAGNOSTICS.replace(old, new)
    problems = _problems_for(write_content(tmp_path, diagnostics=diagnostics))
    assert any(expected_problem in problem for problem in problems), problems


def test_sync_stores_answers_as_json_and_retires_removed_questions(
    conn: sqlite3.Connection, tmp_path: Path
) -> None:
    sync_content(conn, load_content(write_content(tmp_path / "v1")))
    row = conn.execute(
        "SELECT options, accepted_answers FROM diagnostic_questions WHERE slug = 'basics-concept'"
    ).fetchone()
    assert json.loads(row["options"]) == ["certa", "errada"]
    assert json.loads(row["accepted_answers"]) == ["certa"]

    trimmed = SAMPLE_DIAGNOSTICS.split('[[questions]]\nslug = "advanced-concept"')[0]
    report = sync_content(conn, load_content(write_content(tmp_path / "v2", diagnostics=trimmed)))
    assert report.retired_questions == ("advanced-concept",)
    retired = conn.execute(
        "SELECT retired FROM diagnostic_questions WHERE slug = 'advanced-concept'"
    ).fetchone()[0]
    assert retired == 1

    sync_content(conn, load_content(write_content(tmp_path / "v3")))
    retired = conn.execute(
        "SELECT retired FROM diagnostic_questions WHERE slug = 'advanced-concept'"
    ).fetchone()[0]
    assert retired == 0
