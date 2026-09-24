from __future__ import annotations

from collections.abc import Sequence

import typer
from rich.rule import Rule
from rich.table import Table

from hone.cli.console import (
    challenges_as_exit,
    console,
    mastery_label,
    mastery_meter,
    say_ok,
    status_label,
    status_marker,
)
from hone.core.clock import utc_now
from hone.core.workspace import open_workspace
from hone.engines.knowledge import (
    CompetencyState,
    LearningPath,
    build_knowledge_map,
    build_learning_path,
    clear_goal,
    find_goal_path,
    get_goal_path,
    list_assessed_gaps,
    set_goal,
)
from hone.engines.progress import resolve_module
from hone.voice import goal_reached_message, goal_set_message

LIKELY_KNOWN_HINT = "o diagnóstico diz que você já aplica isto"


def register(app: typer.Typer) -> None:
    app.command("map", help="Seu mapa de conhecimento: o nível de domínio em cada competência.")(
        knowledge_map
    )
    app.command("goal", help="Mostra ou define o módulo que você quer alcançar.")(goal)
    app.command("path", help="Pré-requisitos que faltam e a ordem sugerida até o objetivo.")(path)
    app.command("gaps", help="Lacunas: competências que ainda não estão firmes.")(gaps)


def knowledge_map() -> None:
    with challenges_as_exit(), open_workspace() as workspace:
        areas = build_knowledge_map(workspace.conn, workspace.user_id)

    if not areas:
        console.print("Nenhuma competência carregada. Rode [accent]hone content sync[/accent].")
        return

    for area in areas:
        console.print(Rule(f"[muted]{area.name}[/muted]", style="muted", align="left"))
        table = Table(show_header=False, box=None, pad_edge=False)
        for state in area.competencies:
            table.add_row(
                f"[bold]{state.name}[/bold]",
                mastery_meter(state.mastery),
                mastery_label(state.mastery),
            )
        console.print(table)

    assessed_any = any(state.was_assessed for area in areas for state in area.competencies)
    if not assessed_any:
        console.print(
            "\nO mapa ainda está em branco. Descubra o que você já sabe com "
            "[accent]hone diagnostic start[/accent]."
        )


def _print_path(learning_path: LearningPath) -> None:
    goal_module = learning_path.goal
    if learning_path.is_reached:
        say_ok(goal_reached_message(goal_module.title))
        return

    console.print(
        Rule(f"[muted]caminho até “{goal_module.title}”[/muted]", style="muted", align="left")
    )
    for number, step in enumerate(learning_path.steps, start=1):
        module = step.module
        hint = f"  [ok]{LIKELY_KNOWN_HINT}[/ok]" if step.likely_known else ""
        console.print(
            f"{number:>2}. {status_marker(module.status)} [bold]{module.title}[/bold]  "
            f"{status_label(module.status)}  [muted]{module.key}[/muted]{hint}"
        )

    if learning_path.gaps:
        console.print(f"\nLacunas no caminho: {_gap_summary(learning_path.gaps)}")

    next_step = learning_path.next_step
    if next_step is None:
        return
    if next_step.likely_known:
        console.print(
            f"\nPróximo passo: {LIKELY_KNOWN_HINT}. Se concordar, "
            f"[accent]hone done {next_step.module.key}[/accent]; se não, "
            f"[accent]hone read {next_step.module.key}[/accent]."
        )
    else:
        console.print(f"\nPróximo passo: [accent]hone read {next_step.module.key}[/accent]")


def _gap_summary(states: Sequence[CompetencyState]) -> str:
    return ", ".join(f"{state.name} ([muted]{state.mastery.label}[/muted])" for state in states)


def goal(
    module: str | None = typer.Argument(
        None, help="Módulo que você quer alcançar (ex.: searching-and-sorting)."
    ),
    clear: bool = typer.Option(False, "--clear", help="Remove o objetivo atual."),
) -> None:
    with challenges_as_exit(), open_workspace() as workspace:
        if clear:
            clear_goal(workspace.conn, workspace.user_id)
            say_ok("Objetivo removido. O painel volta a sugerir pela ordem das trilhas.")
            return
        if module is not None:
            target = resolve_module(workspace.conn, workspace.user_id, module)
            set_goal(workspace.conn, workspace.user_id, target, utc_now())
            say_ok(goal_set_message(target.title))
        learning_path = find_goal_path(workspace.conn, workspace.user_id)

    if learning_path is None:
        console.print(
            "[muted]Nenhum objetivo definido.[/muted] Escolha um com "
            "[accent]hone goal <módulo>[/accent]."
        )
        return
    _print_path(learning_path)


def path(
    module: str | None = typer.Argument(
        None, help="Módulo de destino. Sem ele, usa o objetivo definido com hone goal."
    ),
) -> None:
    with challenges_as_exit(), open_workspace() as workspace:
        if module is None:
            learning_path = get_goal_path(workspace.conn, workspace.user_id)
        else:
            target = resolve_module(workspace.conn, workspace.user_id, module)
            learning_path = build_learning_path(workspace.conn, workspace.user_id, target)
    _print_path(learning_path)


def gaps() -> None:
    with challenges_as_exit(), open_workspace() as workspace:
        learning_path = find_goal_path(workspace.conn, workspace.user_id)
        states = (
            list(learning_path.gaps)
            if learning_path is not None
            else list_assessed_gaps(workspace.conn, workspace.user_id)
        )

    if learning_path is not None:
        console.print(
            Rule(
                f"[muted]lacunas até “{learning_path.goal.title}”[/muted]",
                style="muted",
                align="left",
            )
        )
    if not states:
        console.print("Nenhuma lacuna à vista. O que está no caminho já está firme.")
    for state in states:
        where = (
            f"  [muted]estude: {', '.join(state.module_keys)}[/muted]" if state.module_keys else ""
        )
        console.print(f"  [bold]{state.name}[/bold]  {mastery_label(state.mastery)}{where}")

    if learning_path is None:
        console.print(
            "\n[muted]Sem objetivo, mostro só o que o diagnóstico apontou. "
            "Com [accent]hone goal <módulo>[/accent] entram também as competências "
            "que você ainda não estudou no caminho.[/muted]"
        )
