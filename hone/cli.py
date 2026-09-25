from __future__ import annotations

import socket
import threading
import webbrowser

import typer

from hone import __version__
from hone.config import Settings, load_settings
from hone.core.db import MigrationError
from hone.startup import StartupReport, prepare_system
from hone.voice import challenge_for

BROWSER_DELAY_SECONDS = 1.0
PORT_CHECK_TIMEOUT_SECONDS = 0.5

app = typer.Typer(add_completion=False)


def _url(settings: Settings) -> str:
    return f"http://{settings.api_host}:{settings.api_port}"


def _is_already_running(settings: Settings) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.settimeout(PORT_CHECK_TIMEOUT_SECONDS)
        return probe.connect_ex((settings.api_host, settings.api_port)) == 0


def _print_startup(report: StartupReport, url: str) -> None:
    greeting = "Oi" if report.first_run else "De volta"
    sync = report.sync
    typer.echo(
        f"{greeting}, {report.user_name}. {sync.modules} módulos, {sync.questions} perguntas "
        f"de diagnóstico e {sync.exercises} exercícios prontos."
    )
    for label, items in (
        ("Módulos que sumiram dos arquivos (seu progresso foi mantido)", sync.orphan_modules),
        ("Perguntas que saíram do diagnóstico", sync.retired_questions),
        ("Exercícios que saíram das trilhas", sync.retired_exercises),
    ):
        if items:
            typer.echo(f"{label}: {', '.join(items)}")
    typer.echo(f"\nautonomia.dev aberto em {url}")
    typer.echo("Deixe esta janela aberta enquanto estuda. Para sair, feche-a ou aperte Ctrl+C.")


def _print_challenge(error: Exception) -> None:
    challenge = challenge_for(error)
    if challenge is None:
        typer.echo(f"Desafio: não consegui abrir o sistema ({error}).", err=True)
        return
    typer.echo(f"Desafio: {challenge.problem}", err=True)
    typer.echo(f"Próximo passo: {challenge.next_step}", err=True)


@app.command(help="Abre o autonomia.dev no navegador.")
def main(
    version: bool = typer.Option(False, "--version", help="Mostra a versão e sai."),
) -> None:
    if version:
        typer.echo(f"hone {__version__}")
        return

    import uvicorn

    settings = load_settings()
    url = _url(settings)
    if _is_already_running(settings):
        typer.echo(f"O autonomia.dev já estava aberto. Abrindo {url} no navegador.")
        webbrowser.open(url)
        return

    try:
        report = prepare_system(settings)
    except MigrationError as error:
        typer.echo(f"Desafio: {error}", err=True)
        raise typer.Exit(code=1) from error
    except Exception as error:
        if challenge_for(error) is None:
            raise
        _print_challenge(error)
        raise typer.Exit(code=1) from error

    _print_startup(report, url)
    threading.Timer(BROWSER_DELAY_SECONDS, webbrowser.open, args=(url,)).start()
    uvicorn.run(
        "hone.api.app:app", host=settings.api_host, port=settings.api_port, log_level="warning"
    )
