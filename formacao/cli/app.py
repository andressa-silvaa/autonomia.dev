from __future__ import annotations

import sqlite3
from contextlib import closing
from pathlib import Path
from typing import NoReturn

import typer
from rich.table import Table

from formacao import __version__
from formacao.cli.console import console, say_challenge, say_ok
from formacao.config import load_settings
from formacao.core.db import (
    MigrationError,
    connect,
    latest_version,
    migrate,
    schema_version,
    table_counts,
)
from formacao.core.users import ensure_default_user

app = typer.Typer(
    help="Sistema Pessoal de Formação em TI.",
    no_args_is_help=True,
    add_completion=False,
)
db_app = typer.Typer(help="Banco de dados local (SQLite).", no_args_is_help=True)
app.add_typer(db_app, name="db")


def _show_version(value: bool) -> None:
    if value:
        console.print(f"formacao [accent]{__version__}[/accent]")
        raise typer.Exit()


def _exit_with_database_challenge(db_path: Path, error: sqlite3.Error | OSError) -> NoReturn:
    say_challenge(
        f"não consegui abrir o banco em {db_path} ({error}).",
        "confira FORMACAO_DB_PATH no .env e se você tem permissão de escrita na pasta.",
    )
    raise typer.Exit(code=1) from error


@app.callback()
def main(
    version: bool = typer.Option(
        False, "--version", help="Mostra a versão e sai.", callback=_show_version, is_eager=True
    ),
) -> None:
    pass


@db_app.command("init", help="Cria o banco (ou aplica migrações pendentes) e registra a usuária.")
def db_init() -> None:
    settings = load_settings()
    try:
        with closing(connect(settings.db_path)) as conn:
            applied = migrate(conn)
            user, created = ensure_default_user(conn, settings.user_name)
            version = schema_version(conn)
    except MigrationError as exc:
        say_challenge(str(exc), "confira o arquivo de migração citado e rode de novo.")
        raise typer.Exit(code=1) from exc
    except (sqlite3.Error, OSError) as exc:
        _exit_with_database_challenge(settings.db_path, exc)

    if applied:
        for migration in applied:
            say_ok(f"migração [accent]{migration.version:04d}[/accent] {migration.name} aplicada")
    else:
        say_ok(f"schema já estava em dia (versão {version})")

    if created:
        console.print(
            f"\n[title]Oi, {user.name}.[/title] O banco está pronto em "
            f"[muted]{settings.db_path}[/muted]."
        )
        console.print("Página em branco é só o começo da história. Bora escrever a primeira.")
    else:
        console.print(f"\n[title]De volta, {user.name}.[/title] Tudo no lugar.")


@db_app.command("status", help="Mostra a versão do schema e quantas linhas cada tabela tem.")
def db_status() -> None:
    settings = load_settings()
    if not settings.db_path.exists():
        say_challenge(
            f"ainda não existe banco em {settings.db_path}.",
            "rode [accent]formacao db init[/accent].",
        )
        raise typer.Exit(code=1)

    latest = latest_version()
    try:
        with closing(connect(settings.db_path)) as conn:
            version = schema_version(conn)
            counts = table_counts(conn)
    except (sqlite3.Error, OSError) as exc:
        _exit_with_database_challenge(settings.db_path, exc)

    pending_count = latest - version
    status = (
        "[ok]em dia[/ok]"
        if pending_count == 0
        else f"[warning]{pending_count} pendente(s)[/warning]"
    )
    console.print(f"[title]Banco[/title] [muted]{settings.db_path}[/muted]")
    console.print(f"Schema: versão {version} de {latest} — {status}\n")

    table = Table(show_edge=False, header_style="muted", box=None, pad_edge=False)
    table.add_column("tabela")
    table.add_column("linhas", justify="right")
    for name, count in counts.items():
        table.add_row(name, f"[accent]{count}[/accent]" if count else "[muted]0[/muted]")
    console.print(table)


@app.command(help="Sobe a API local. Documentação automática em /docs.")
def serve(
    reload: bool = typer.Option(False, help="Reinicia sozinho ao salvar código (desenvolvimento)."),
) -> None:
    import uvicorn

    settings = load_settings()
    console.print(
        f"API em [accent]http://{settings.api_host}:{settings.api_port}[/accent] "
        "[muted](Ctrl+C para parar)[/muted]"
    )
    uvicorn.run(
        "formacao.api.app:app", host=settings.api_host, port=settings.api_port, reload=reload
    )
