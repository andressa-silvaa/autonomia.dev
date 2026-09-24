from __future__ import annotations

import sqlite3
import time
from dataclasses import dataclass

import typer
from rich.markdown import Markdown
from rich.markup import escape
from rich.rule import Rule
from rich.table import Table

from hone.cli.console import challenges_as_exit, console, mastery_label, mastery_meter, say_ok
from hone.core.clock import utc_now
from hone.core.models import AnswerConfidence
from hone.core.workspace import open_workspace
from hone.engines.diagnostic import (
    AnswerOutcome,
    DiagnosticReport,
    Question,
    finish_run,
    latest_report,
    next_question,
    record_answer,
    start_or_resume_run,
)
from hone.voice import (
    answer_feedback_message,
    diagnostic_finished_message,
    diagnostic_resumed_message,
    diagnostic_started_message,
)

PAUSE_WORD = "pausar"
DONT_KNOW_CHOICE = 0
CONFIDENCE_CHOICES = {"s": AnswerConfidence.SURE, "c": AnswerConfidence.GUESS}
DEFAULT_CONFIDENCE_CHOICE = "s"

diagnostic_app = typer.Typer(
    help="Diagnóstico inicial: descobre o que você já sabe e alimenta o mapa.",
    no_args_is_help=True,
)


@dataclass(frozen=True, slots=True)
class Response:
    answer: str
    confidence: AnswerConfidence
    duration_seconds: int


def _is_pause(raw: str) -> bool:
    return raw.strip().casefold() == PAUSE_WORD


def _ask_choice(option_count: int) -> int | None:
    while True:
        raw = typer.prompt(
            f"Sua resposta (1-{option_count}, {DONT_KNOW_CHOICE} = não sei, {PAUSE_WORD} = parar)"
        )
        if _is_pause(raw):
            return None
        if raw.strip().isdigit() and DONT_KNOW_CHOICE <= int(raw) <= option_count:
            return int(raw)
        console.print(
            f"[warning]Digite um número de {DONT_KNOW_CHOICE} a {option_count}.[/warning]"
        )


def _ask_confidence() -> AnswerConfidence:
    while True:
        raw = typer.prompt(
            "Você sabia ou chutou? (s = sabia, c = chutei)", default=DEFAULT_CONFIDENCE_CHOICE
        )
        confidence = CONFIDENCE_CHOICES.get(raw.strip().casefold())
        if confidence is not None:
            return confidence
        console.print("[warning]Responda s ou c.[/warning]")


def _print_question(question: Question, position: int, total: int) -> None:
    heading = f"{position}/{total} · {question.competency_name} · {question.kind.label}"
    console.print()
    console.print(Rule(f"[muted]{heading}[/muted]", style="muted", align="left"))
    console.print(Markdown(question.prompt))
    for number, option in enumerate(question.options, start=1):
        console.print(f"  [accent]{number}[/accent]  {escape(option)}")
    if question.is_choice:
        console.print(f"  [muted]{DONT_KNOW_CHOICE}  não sei[/muted]")


def _ask(question: Question) -> Response | None:
    started = time.monotonic()
    if question.is_choice:
        choice = _ask_choice(len(question.options))
        if choice is None:
            return None
        answer = question.options[choice - 1] if choice != DONT_KNOW_CHOICE else ""
    else:
        answer = typer.prompt(
            f"Sua resposta (vazio = não sei, {PAUSE_WORD} = parar)", default="", show_default=False
        )
        if _is_pause(answer):
            return None

    duration = round(time.monotonic() - started)
    if not answer.strip():
        return Response("", AnswerConfidence.DONT_KNOW, duration)
    return Response(answer, _ask_confidence(), duration)


def _print_feedback(outcome: AnswerOutcome) -> None:
    style = "ok" if outcome.is_correct else "challenge"
    console.print(f"[{style}]{answer_feedback_message(outcome)}[/{style}]")
    if not outcome.is_correct:
        console.print(f"Resposta: [accent]{escape(outcome.correct_answer)}[/accent]")
    if outcome.explanation:
        console.print(f"[muted]{escape(outcome.explanation)}[/muted]")


def _print_report(report: DiagnosticReport) -> None:
    console.print(
        Rule(
            f"[muted]diagnóstico de {report.finished_at.astimezone().strftime('%d/%m')}[/muted]",
            style="muted",
            align="left",
        )
    )
    table = Table(show_header=False, box=None, pad_edge=False)
    for result in report.results:
        guesses = f" · {result.guessed_count} no chute" if result.guessed_count else ""
        table.add_row(
            f"[bold]{result.competency_name}[/bold]",
            mastery_meter(result.assessed),
            mastery_label(result.assessed),
            f"[muted]{result.correct_count}/{result.answered_count} certas{guesses}[/muted]",
        )
    console.print(table)
    solid_count = sum(result.is_solid for result in report.results)
    console.print(f"\n{diagnostic_finished_message(solid_count, len(report.results))}")
    console.print(
        "Próximo passo: [accent]hone map[/accent] para ver o mapa, "
        "ou [accent]hone goal <módulo>[/accent] para escolher aonde quer chegar."
    )


def _run_questions(conn: sqlite3.Connection, run_id: int, answered: int, total: int) -> bool:
    position = answered
    while (question := next_question(conn, run_id)) is not None:
        position += 1
        _print_question(question, position, total)
        response = _ask(question)
        if response is None:
            return False
        outcome = record_answer(
            conn,
            run_id,
            question,
            response.answer,
            response.confidence,
            response.duration_seconds,
            utc_now(),
        )
        _print_feedback(outcome)
    return True


@diagnostic_app.command("start", help="Começa o diagnóstico, ou continua de onde você parou.")
def diagnostic_start() -> None:
    with challenges_as_exit(), open_workspace() as workspace:
        run, resumed = start_or_resume_run(workspace.conn, workspace.user_id, utc_now())
        if resumed:
            say_ok(diagnostic_resumed_message(run.answered_count, run.total_count))
        else:
            say_ok(diagnostic_started_message(run.total_count))
        console.print(
            f"[muted]Pode parar quando quiser digitando “{PAUSE_WORD}”: "
            "as respostas ficam salvas.[/muted]"
        )

        completed = _run_questions(workspace.conn, run.id, run.answered_count, run.total_count)
        if not completed:
            console.print("\nPausado. Quando voltar: [accent]hone diagnostic start[/accent]")
            return
        report = finish_run(workspace.conn, workspace.user_id, utc_now())

    console.print()
    _print_report(report)


@diagnostic_app.command("result", help="Mostra o resultado do último diagnóstico concluído.")
def diagnostic_result() -> None:
    with challenges_as_exit(), open_workspace() as workspace:
        report = latest_report(workspace.conn, workspace.user_id)
    _print_report(report)
