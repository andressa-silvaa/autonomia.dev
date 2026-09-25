from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path

from hone.core.models import QuestionKind
from hone.engines.toml_tables import TableReader, read_tables, read_toml

DIAGNOSTICS_DIRNAME = "diagnostics"
MIN_CHOICE_OPTIONS = 2


@dataclass(frozen=True, slots=True)
class QuestionDefinition:
    slug: str
    competency_slug: str
    kind: QuestionKind | None
    prompt: str
    options: tuple[str, ...]
    accepted_answers: tuple[str, ...]
    explanation: str


def diagnostics_root(content_dir: Path) -> Path:
    return content_dir / DIAGNOSTICS_DIRNAME


def _parse_kind(reader: TableReader, location: str, problems: list[str]) -> QuestionKind | None:
    kind_text = reader.text("kind")
    try:
        return QuestionKind(kind_text)
    except ValueError:
        if kind_text:
            valid = ", ".join(kind.value for kind in QuestionKind)
            problems.append(f"{location}: unknown kind '{kind_text}' (use one of: {valid})")
        return None


def _parse_choice_answer(
    reader: TableReader, options: tuple[str, ...], location: str, problems: list[str]
) -> tuple[str, ...]:
    if len(options) < MIN_CHOICE_OPTIONS:
        problems.append(
            f"{location}: a choice question needs at least {MIN_CHOICE_OPTIONS} options"
        )
        return ()
    if len(set(options)) != len(options):
        problems.append(f"{location}: options must be different from each other")
    answer = reader.integer("answer")
    if answer is None:
        return ()
    if not 1 <= answer <= len(options):
        problems.append(f"{location}: answer must be between 1 and {len(options)}")
        return ()
    return (options[answer - 1],)


def parse_answer_key(
    reader: TableReader, options: tuple[str, ...], location: str, problems: list[str]
) -> tuple[str, ...]:
    if reader.has("options") and reader.has("accept"):
        problems.append(f"{location}: use either 'options' + 'answer' or 'accept', not both")
        return ()
    if reader.has("options"):
        return _parse_choice_answer(reader, options, location, problems)

    accepted = tuple(answer.strip() for answer in reader.text_list("accept") if answer.strip())
    if not accepted:
        problems.append(f"{location}: a typed question needs a non-empty 'accept' list")
    return accepted


def _parse_question(table: dict, location: str, problems: list[str]) -> QuestionDefinition:
    reader = TableReader(table, location, problems)
    options = tuple(option.strip() for option in reader.text_list("options"))
    return QuestionDefinition(
        slug=reader.text("slug"),
        competency_slug=reader.text("competency"),
        kind=_parse_kind(reader, location, problems),
        prompt=reader.text("prompt"),
        options=options,
        accepted_answers=parse_answer_key(reader, options, location, problems),
        explanation=reader.text("explanation", required=False),
    )


def parse_questions(content_dir: Path, problems: list[str]) -> tuple[QuestionDefinition, ...]:
    root = diagnostics_root(content_dir)
    if not root.is_dir():
        return ()

    questions = []
    for path in sorted(root.glob("*.toml")):
        document = read_toml(path, problems)
        for index, table in enumerate(read_tables(document, "questions", path, problems), start=1):
            location = f"{DIAGNOSTICS_DIRNAME}/{path.name} question #{index}"
            questions.append(_parse_question(table, location, problems))
    return tuple(questions)


def validate_questions(
    questions: tuple[QuestionDefinition, ...], competency_slugs: set[str], problems: list[str]
) -> None:
    seen: set[str] = set()
    for question in questions:
        if question.slug in seen:
            problems.append(f"duplicate question slug '{question.slug}'")
        seen.add(question.slug)
        if question.competency_slug not in competency_slugs:
            problems.append(
                f"question '{question.slug}' uses unknown competency '{question.competency_slug}'"
            )


def sync_questions(
    conn: sqlite3.Connection, questions: tuple[QuestionDefinition, ...]
) -> tuple[str, ...]:
    conn.executemany(
        "INSERT INTO diagnostic_questions "
        "(competency_id, slug, kind, prompt, options, accepted_answers, explanation, position, "
        "retired) "
        "VALUES ((SELECT id FROM competencies WHERE slug = ?), ?, ?, ?, ?, ?, ?, ?, 0) "
        "ON CONFLICT (slug) DO UPDATE SET competency_id = excluded.competency_id, "
        "kind = excluded.kind, prompt = excluded.prompt, options = excluded.options, "
        "accepted_answers = excluded.accepted_answers, explanation = excluded.explanation, "
        "position = excluded.position, retired = 0",
        [
            (
                question.competency_slug,
                question.slug,
                question.kind,
                question.prompt,
                json.dumps(question.options, ensure_ascii=False),
                json.dumps(question.accepted_answers, ensure_ascii=False),
                question.explanation,
                position,
            )
            for position, question in enumerate(questions, start=1)
        ],
    )

    defined_slugs = {question.slug for question in questions}
    retired = tuple(
        sorted(
            row["slug"]
            for row in conn.execute("SELECT slug FROM diagnostic_questions")
            if row["slug"] not in defined_slugs
        )
    )
    conn.executemany(
        "UPDATE diagnostic_questions SET retired = 1 WHERE slug = ?", [(slug,) for slug in retired]
    )
    return retired
