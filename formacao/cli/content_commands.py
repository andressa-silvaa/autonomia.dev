from __future__ import annotations

import typer

from formacao.cli.console import challenges_as_exit, console, say_ok
from formacao.core.workspace import open_workspace
from formacao.engines.content import load_content, sync_content

content_app = typer.Typer(help="Conteúdo das trilhas (arquivos em data/).", no_args_is_help=True)


@content_app.command(
    "sync", help="Valida os arquivos de data/ e carrega áreas, trilhas e módulos no banco."
)
def content_sync() -> None:
    with challenges_as_exit(), open_workspace() as workspace:
        content = load_content(workspace.settings.content_dir)
        report = sync_content(workspace.conn, content)

    say_ok(
        f"{report.areas} áreas, {report.competencies} competências, "
        f"{report.tracks} trilha(s) e [accent]{report.modules}[/accent] módulos sincronizados"
    )
    if report.orphan_modules:
        console.print(
            "[warning]Estes módulos estão no banco, mas sumiram dos arquivos "
            "(mantive o seu progresso neles):[/warning]"
        )
        for key in report.orphan_modules:
            console.print(f"  [muted]{key}[/muted]")
    console.print("Próximo passo: [accent]formacao tracks[/accent] para ver por onde começar.")
