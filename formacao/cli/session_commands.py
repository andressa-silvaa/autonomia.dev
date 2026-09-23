from __future__ import annotations

import typer

from formacao.cli.console import challenges_as_exit, console, say_ok
from formacao.core.clock import utc_now
from formacao.core.workspace import open_workspace
from formacao.engines.progress import resolve_module, start_module
from formacao.engines.sessions import (
    SessionView,
    find_active_session,
    start_session,
    stop_session,
)
from formacao.voice import session_stopped_message

session_app = typer.Typer(help="Sessões de estudo cronometradas.", no_args_is_help=True)


def _topic(session: SessionView) -> str:
    return f" em [accent]{session.module_title}[/accent]" if session.module_title else ""


@session_app.command("start", help="Começa a cronometrar uma sessão de estudo.")
def session_start(
    module: str | None = typer.Argument(None, help="Módulo que você vai estudar (ex.: recursao)."),
) -> None:
    with challenges_as_exit(), open_workspace() as workspace:
        now = utc_now()
        module_id = None
        if module is not None:
            target = resolve_module(workspace.conn, workspace.user_id, module)
            start_module(workspace.conn, workspace.user_id, target, now)
            module_id = target.id
        session = start_session(workspace.conn, workspace.user_id, module_id, now)

    say_ok(f"Sessão começou{_topic(session)}. Celular longe, foco perto.")
    console.print("Quando terminar: [accent]formacao session stop[/accent]")


@session_app.command("stop", help="Encerra a sessão atual.")
def session_stop(
    notes: str = typer.Option(
        "", "--notes", "-n", help="O que você fez ou descobriu nesta sessão."
    ),
) -> None:
    with challenges_as_exit(), open_workspace() as workspace:
        session = stop_session(workspace.conn, workspace.user_id, notes, utc_now())
    say_ok(session_stopped_message(session.elapsed_minutes(utc_now())))


@session_app.command("status", help="Mostra se há uma sessão rolando e há quanto tempo.")
def session_status() -> None:
    with challenges_as_exit(), open_workspace() as workspace:
        session = find_active_session(workspace.conn, workspace.user_id)
    if session is None:
        console.print(
            "[muted]Nenhuma sessão aberta.[/muted] "
            "Comece com [accent]formacao session start[/accent]."
        )
        return
    minutes = session.elapsed_minutes(utc_now())
    console.print(f"Sessão rolando{_topic(session)} há [accent]{minutes} min[/accent].")
