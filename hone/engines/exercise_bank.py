from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path

from hone.core.models import AnswerFormat, ExerciseKind, GradingMethod
from hone.engines.question_bank import parse_answer_key
from hone.engines.toml_tables import TableReader, read_toml

EXERCISE_FILENAME = "exercise.toml"
STATEMENT_FILENAME = "README.md"
STARTER_FILENAME = "starter.py"
TESTS_FILENAME = "test_solution.py"
REFERENCE_FILENAME = "reference.md"
MIN_DIFFICULTY = 1
MAX_DIFFICULTY = 5
BASE_XP_BY_DIFFICULTY = {1: 5, 2: 10, 3: 20, 4: 35, 5: 50}
ANSWER_BASED_FORMATS = {AnswerFormat.CHOICE, AnswerFormat.TYPED, AnswerFormat.CODE}


@dataclass(frozen=True, slots=True)
class ExerciseDefinition:
    slug: str
    track_slug: str
    module_slug: str
    title: str
    kind: ExerciseKind | None
    grading: GradingMethod | None
    answer_format: AnswerFormat | None
    statement: str
    difficulty: int
    required: bool
    options: tuple[str, ...]
    accepted_answers: tuple[str, ...]
    rubric: tuple[str, ...]
    hints: tuple[str, ...]
    reference_answer: str
    source_path: str

    @property
    def module_key(self) -> str:
        return f"{self.track_slug}/{self.module_slug}"

    @property
    def base_xp(self) -> int:
        return BASE_XP_BY_DIFFICULTY.get(self.difficulty, 0)


def detect_answer_format(
    options: tuple[str, ...], has_accept: bool, has_tests: bool, rubric: tuple[str, ...]
) -> list[AnswerFormat]:
    detected = []
    if options:
        detected.append(AnswerFormat.CHOICE)
    if has_accept:
        detected.append(AnswerFormat.TYPED)
    if has_tests:
        detected.append(AnswerFormat.CODE)
    if rubric:
        detected.append(AnswerFormat.TEXT)
    return detected


def _parse_enum[EnumType: (ExerciseKind, GradingMethod)](
    enum_type: type[EnumType], reader: TableReader, key: str, location: str, problems: list[str]
) -> EnumType | None:
    text = reader.text(key)
    try:
        return enum_type(text)
    except ValueError:
        if text:
            valid = ", ".join(member.value for member in enum_type)
            problems.append(f"{location}: unknown {key} '{text}' (use one of: {valid})")
        return None


def _read_optional_file(path: Path) -> str:
    return path.read_text(encoding="utf-8").strip() if path.is_file() else ""


def _check_format_rules(
    exercise_dir: Path,
    answer_formats: list[AnswerFormat],
    grading: GradingMethod | None,
    location: str,
    problems: list[str],
) -> AnswerFormat | None:
    if len(answer_formats) != 1:
        problems.append(
            f"{location}: define exactly one answer format: 'options' + 'answer', 'accept', "
            f"a {TESTS_FILENAME} file or a 'rubric'"
        )
        return None

    answer_format = answer_formats[0]
    if answer_format is AnswerFormat.CODE and not (exercise_dir / STARTER_FILENAME).is_file():
        problems.append(f"{location}: code exercises need a {STARTER_FILENAME} file")
    if grading is None:
        return answer_format
    if answer_format in ANSWER_BASED_FORMATS and grading is not GradingMethod.AUTOMATED_TESTS:
        problems.append(f"{location}: {answer_format} answers must use grading = 'auto'")
    if answer_format is AnswerFormat.TEXT and grading is GradingMethod.AUTOMATED_TESTS:
        problems.append(f"{location}: rubric answers must use grading = 'ollama' or 'self'")
    return answer_format


def _parse_exercise(
    exercise_dir: Path, exercises_dir: Path, problems: list[str]
) -> ExerciseDefinition:
    relative = exercise_dir.relative_to(exercises_dir)
    track_slug, module_slug, slug = relative.parts
    location = f"exercises/{relative.as_posix()}/{EXERCISE_FILENAME}"
    reader = TableReader(read_toml(exercise_dir / EXERCISE_FILENAME, problems), location, problems)

    statement = _read_optional_file(exercise_dir / STATEMENT_FILENAME)
    if not statement:
        problems.append(f"{location}: missing or empty {STATEMENT_FILENAME}")

    difficulty = reader.integer("difficulty") or 0
    if difficulty and not MIN_DIFFICULTY <= difficulty <= MAX_DIFFICULTY:
        problems.append(
            f"{location}: difficulty must be between {MIN_DIFFICULTY} and {MAX_DIFFICULTY}"
        )

    options = tuple(option.strip() for option in reader.text_list("options"))
    rubric = tuple(item.strip() for item in reader.text_list("rubric") if item.strip())
    has_tests = (exercise_dir / TESTS_FILENAME).is_file()
    grading = _parse_enum(GradingMethod, reader, "grading", location, problems)
    answer_format = _check_format_rules(
        exercise_dir,
        detect_answer_format(options, reader.has("accept"), has_tests, rubric),
        grading,
        location,
        problems,
    )
    accepted = (
        parse_answer_key(reader, options, location, problems)
        if answer_format in (AnswerFormat.CHOICE, AnswerFormat.TYPED)
        else ()
    )

    return ExerciseDefinition(
        slug=slug,
        track_slug=track_slug,
        module_slug=module_slug,
        title=reader.text("title"),
        kind=_parse_enum(ExerciseKind, reader, "kind", location, problems),
        grading=grading,
        answer_format=answer_format,
        statement=statement,
        difficulty=difficulty,
        required=reader.boolean("required", default=False),
        options=options,
        accepted_answers=accepted,
        rubric=rubric,
        hints=tuple(hint.strip() for hint in reader.text_list("hints") if hint.strip()),
        reference_answer=_read_optional_file(exercise_dir / REFERENCE_FILENAME),
        source_path=relative.as_posix(),
    )


def parse_exercises(
    exercises_dir: Path | None, problems: list[str]
) -> tuple[ExerciseDefinition, ...]:
    if exercises_dir is None or not exercises_dir.is_dir():
        return ()
    exercise_dirs = sorted(path.parent for path in exercises_dir.glob(f"*/*/*/{EXERCISE_FILENAME}"))
    return tuple(_parse_exercise(path, exercises_dir, problems) for path in exercise_dirs)


def validate_exercises(
    exercises: tuple[ExerciseDefinition, ...], module_keys: set[str], problems: list[str]
) -> None:
    seen: set[str] = set()
    for exercise in exercises:
        if exercise.slug in seen:
            problems.append(f"duplicate exercise slug '{exercise.slug}'")
        seen.add(exercise.slug)
        if exercise.module_key not in module_keys:
            problems.append(
                f"exercise '{exercise.slug}' lives in unknown module '{exercise.module_key}'"
            )


def sync_exercises(
    conn: sqlite3.Connection, exercises: tuple[ExerciseDefinition, ...]
) -> tuple[str, ...]:
    conn.executemany(
        "INSERT INTO exercises (module_id, slug, title, kind, grading, prompt, difficulty, xp, "
        "required, options, accepted_answers, rubric, hints, reference_answer, source_path, "
        "position, retired) "
        "VALUES ((SELECT modules.id FROM modules JOIN tracks ON tracks.id = modules.track_id "
        "WHERE tracks.slug = ? AND modules.slug = ?), ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, "
        "0) "
        "ON CONFLICT (slug) DO UPDATE SET module_id = excluded.module_id, title = excluded.title, "
        "kind = excluded.kind, grading = excluded.grading, prompt = excluded.prompt, "
        "difficulty = excluded.difficulty, xp = excluded.xp, required = excluded.required, "
        "options = excluded.options, accepted_answers = excluded.accepted_answers, "
        "rubric = excluded.rubric, hints = excluded.hints, "
        "reference_answer = excluded.reference_answer, source_path = excluded.source_path, "
        "position = excluded.position, retired = 0",
        [
            (
                exercise.track_slug,
                exercise.module_slug,
                exercise.slug,
                exercise.title,
                exercise.kind,
                exercise.grading,
                exercise.statement,
                exercise.difficulty,
                exercise.base_xp,
                int(exercise.required),
                json.dumps(exercise.options, ensure_ascii=False),
                json.dumps(exercise.accepted_answers, ensure_ascii=False),
                json.dumps(exercise.rubric, ensure_ascii=False),
                json.dumps(exercise.hints, ensure_ascii=False),
                exercise.reference_answer,
                exercise.source_path,
                position,
            )
            for position, exercise in enumerate(exercises, start=1)
        ],
    )

    defined_slugs = {exercise.slug for exercise in exercises}
    retired = tuple(
        sorted(
            row["slug"]
            for row in conn.execute("SELECT slug FROM exercises")
            if row["slug"] not in defined_slugs
        )
    )
    conn.executemany(
        "UPDATE exercises SET retired = 1, required = 0 WHERE slug = ?",
        [(slug,) for slug in retired],
    )
    return retired
