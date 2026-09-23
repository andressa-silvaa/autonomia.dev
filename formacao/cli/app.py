from __future__ import annotations

import webbrowser

import typer

from formacao import __version__
from formacao.cli import study_commands
from formacao.cli.console import console
from formacao.cli.content_commands import content_app
from formacao.cli.db_commands import db_app
from formacao.cli.session_commands import session_app
from formacao.config import load_settings

app = typer.Typer(
    help="Sistema Pessoal de Formação em TI.",
    no_args_is_help=True,
    add_completion=False,
)
app.add_typer(db_app, name="db")
app.add_typer(content_app, name="content")
app.add_typer(session_app, name="session")
study_commands.register(app)


def _show_version(value: bool) -> None:
    if value:
        console.print(f"formacao [accent]{__version__}[/accent]")
        raise typer.Exit()


@app.callback()
def main(
    version: bool = typer.Option(
        False, "--version", help="Mostra a versão e sai.", callback=_show_version, is_eager=True
    ),
) -> None:
    pass


@app.command(help="Sobe a API local e o dashboard. Documentação da API em /docs.")
def serve(
    open_browser: bool = typer.Option(False, "--open", help="Abre o dashboard no navegador."),
    reload: bool = typer.Option(False, help="Reinicia sozinho ao salvar código (desenvolvimento)."),
) -> None:
    import uvicorn

    settings = load_settings()
    url = f"http://{settings.api_host}:{settings.api_port}"
    console.print(f"Dashboard em [accent]{url}[/accent] [muted](Ctrl+C para parar)[/muted]")
    if open_browser:
        webbrowser.open(url)
    uvicorn.run(
        "formacao.api.app:app", host=settings.api_host, port=settings.api_port, reload=reload
    )
