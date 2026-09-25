from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ElementTree
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from hone.core.models import GradingMethod
from hone.engines.ollama import chat_json

PASSING_RUBRIC_SHARE = 2 / 3
OLLAMA_GRADING_TIMEOUT_SECONDS = 300
SOLUTION_MODULE_FILENAME = "solution.py"
TESTS_MODULE_FILENAME = "test_solution.py"
REPORT_FILENAME = "report.xml"
MAX_OUTPUT_LINES = 15

RUBRIC_SCHEMA = {
    "type": "object",
    "properties": {
        "criteria": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "met": {"type": "boolean"},
                    "comment": {"type": "string"},
                },
                "required": ["met", "comment"],
            },
        },
        "feedback": {"type": "string"},
    },
    "required": ["criteria", "feedback"],
}

GRADER_SYSTEM_PROMPT = (
    "You are a demanding but kind programming teacher grading a student's written answer. "
    "Judge each rubric criterion independently, in the given order: met is true only when the "
    "answer clearly satisfies that criterion. Accept any valid wording or approach; the "
    "reference answer is one good answer, not the only one. Value explanation, coherence and "
    "trade-offs over keywords. Write every comment and the final feedback in Brazilian "
    "Portuguese, talking directly to the student as 'você', short and specific. "
    "Return only the requested JSON, with exactly one criteria item per rubric line."
)


class RubricGradingError(Exception):
    pass


@dataclass(frozen=True, slots=True)
class TestFailure:
    name: str
    message: str


@dataclass(frozen=True, slots=True)
class TestRunResult:
    passed: int
    total: int
    failures: tuple[TestFailure, ...]
    timed_out: bool
    output: str

    @property
    def score(self) -> float:
        return self.passed / self.total if self.total else 0.0

    @property
    def is_passing(self) -> bool:
        return self.total > 0 and self.passed == self.total and not self.timed_out


@dataclass(frozen=True, slots=True)
class CriterionResult:
    criterion: str
    met: bool
    comment: str


@dataclass(frozen=True, slots=True)
class RubricResult:
    criteria: tuple[CriterionResult, ...]
    feedback: str
    graded_by: GradingMethod

    @property
    def score(self) -> float:
        return (
            sum(item.met for item in self.criteria) / len(self.criteria) if self.criteria else 0.0
        )

    @property
    def is_passing(self) -> bool:
        return self.score >= PASSING_RUBRIC_SHARE


def normalize_answer(text: str) -> str:
    return "".join(text.split()).casefold()


def matches_accepted_answer(answer: str, accepted_answers: Sequence[str]) -> bool:
    normalized = normalize_answer(answer)
    return bool(normalized) and any(
        normalized == normalize_answer(accepted) for accepted in accepted_answers
    )


def _tail(text: str) -> str:
    return "\n".join(text.strip().splitlines()[-MAX_OUTPUT_LINES:])


def _failure_of(case: ElementTree.Element) -> TestFailure | None:
    for tag in ("failure", "error"):
        problem = case.find(tag)
        if problem is not None:
            message = problem.get("message") or (problem.text or "").strip()
            return TestFailure(case.get("name", "?"), message.splitlines()[0] if message else "")
    return None


def _read_report(report_path: Path, output: str) -> TestRunResult:
    if not report_path.is_file():
        return TestRunResult(0, 0, (), False, _tail(output))
    cases = list(ElementTree.parse(report_path).getroot().iter("testcase"))
    failures = tuple(failure for case in cases if (failure := _failure_of(case)) is not None)
    skipped = sum(case.find("skipped") is not None for case in cases)
    total = len(cases) - skipped
    return TestRunResult(total - len(failures), total, failures, False, _tail(output))


def run_python_tests(solution_path: Path, tests_path: Path, timeout_seconds: int) -> TestRunResult:
    with tempfile.TemporaryDirectory(prefix="hone-exercise-") as temp_dir:
        sandbox = Path(temp_dir)
        shutil.copyfile(solution_path, sandbox / SOLUTION_MODULE_FILENAME)
        shutil.copyfile(tests_path, sandbox / TESTS_MODULE_FILENAME)
        report_path = sandbox / REPORT_FILENAME
        command = [
            sys.executable,
            "-m",
            "pytest",
            "-q",
            "-p",
            "no:cacheprovider",
            f"--junitxml={report_path}",
            TESTS_MODULE_FILENAME,
        ]
        environment = os.environ | {"PYTHONDONTWRITEBYTECODE": "1", "PYTHONIOENCODING": "utf-8"}
        try:
            completed = subprocess.run(
                command,
                cwd=sandbox,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout_seconds,
                env=environment,
                check=False,
            )
        except subprocess.TimeoutExpired:
            return TestRunResult(0, 0, (), True, "")
        return _read_report(report_path, completed.stdout + completed.stderr)


def _rubric_prompt(statement: str, rubric: Sequence[str], reference: str, answer: str) -> str:
    numbered = "\n".join(f"{number}. {item}" for number, item in enumerate(rubric, start=1))
    reference_block = reference or "(no reference answer)"
    return (
        f"## Exercise\n{statement}\n\n## Rubric\n{numbered}\n\n"
        f"## Reference answer\n{reference_block}\n\n## Student answer\n{answer}"
    )


def grade_with_ollama(
    base_url: str,
    model: str,
    statement: str,
    rubric: Sequence[str],
    reference: str,
    answer: str,
) -> RubricResult:
    body = chat_json(
        base_url,
        model,
        GRADER_SYSTEM_PROMPT,
        _rubric_prompt(statement, rubric, reference, answer),
        RUBRIC_SCHEMA,
        OLLAMA_GRADING_TIMEOUT_SECONDS,
    )
    items = body.get("criteria")
    if not isinstance(items, list) or len(items) != len(rubric):
        raise RubricGradingError("The model did not judge every rubric criterion")
    return RubricResult(
        criteria=tuple(
            CriterionResult(criterion, bool(item.get("met")), str(item.get("comment", "")).strip())
            for criterion, item in zip(rubric, items, strict=True)
        ),
        feedback=str(body.get("feedback", "")).strip(),
        graded_by=GradingMethod.LOCAL_AI,
    )


def self_assessed_result(rubric: Sequence[str], met_flags: Sequence[bool]) -> RubricResult:
    return RubricResult(
        criteria=tuple(
            CriterionResult(criterion, met, "")
            for criterion, met in zip(rubric, met_flags, strict=True)
        ),
        feedback="",
        graded_by=GradingMethod.SELF_ASSESSMENT,
    )
