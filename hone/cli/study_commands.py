from __future__ import annotations

import typer
from rich.markdown import Markdown
from rich.rule import Rule
from rich.table import Table

from hone.cli.console import (
    challenges_as_exit,
    console,
    progress_bar,
    say_ok,
    status_label,
    status_marker,
)
from hone.core.clock import local_today, utc_now
from hone.core.workspace import open_workspace
from hone.engines.checkins import check_in, get_streak
from hone.engines.content import read_module_content
from hone.engines.overview import build_overview
from hone.engines.progress import (
    ModuleStatus,
    ModuleView,
    TrackView,
    complete_module,
    find_track_view,
    list_track_views,
    resolve_module,
    start_module,
)
from hone.voice import (
    checkin_saved_message,
    module_completed_message,
    streak_message,
    track_completed_message,
)


def _print_track_progress(tracks: list[TrackView]) -> None:
    table = Table(show_header=False, box=None, pad_edge=False)
    for track in tracks:
        table.add_row(
            f"[bold]{track.name}[/bold]",
            progress_bar(track.completed_count, track.total_count),
            f"[muted]{track.completed_count}/{track.total_count}[/muted]",
            f"[muted]{track.slug}[/muted]",
        )
    console.print(table)


def _print_next_modules(modules: list[ModuleView]) -> None:
    for module in modules:
        console.print(
            f"  {status_marker(module.status)} {module.title}  [muted]{module.key}[/muted]"
        )


def register(app: typer.Typer) -> None:
    app.command("today", help="Seu painel do dia: streak, check-in, sessão e o que estudar agora.")(
        today
    )
    app.command("checkin", help="Registra o check-in do dia com a sua intenção de estudo.")(checkin)
    app.command("tracks", help="Lista as trilhas e o seu progresso em cada uma.")(tracks)
    app.command("track", help="Mostra os módulos de uma trilha e o que já está liberado.")(track)
    app.command("read", help="Abre o conteúdo de um módulo no terminal.")(read)
    app.command("done", help="Marca um módulo como concluído.")(done)


def today() -> None:
    with challenges_as_exit(), open_workspace() as workspace:
        overview = build_overview(workspace.conn, workspace.user_id, local_today(), utc_now())
        user_name = workspace.user.name

    console.print(f"[title]{user_name}, hoje é {overview.today.strftime('%d/%m')}.[/title]")
    console.print(f"[accent]{overview.streak.current}[/accent] {streak_message(overview.streak)}\n")

    if overview.todays_checkin is None:
        console.print("Check-in: [warning]pendente[/warning] — [accent]hone checkin[/accent]")
    else:
        console.print(
            f"Check-in: [ok]feito[/ok] — [muted]{overview.todays_checkin.intention}[/muted]"
        )

    if overview.active_session is not None:
        minutes = overview.active_session.elapsed_minutes(utc_now())
        topic = overview.active_session.module_title or "estudo livre"
        console.print(f"Sessão: [accent]rolando há {minutes} min[/accent] — {topic}")

    if not overview.tracks:
        console.print("\nNenhuma trilha carregada. Rode [accent]hone content sync[/accent].")
        return

    if overview.next_modules:
        heading = "continue daqui"
        if overview.goal_path is not None and not overview.goal_path.is_reached:
            heading = f"continue daqui, rumo a “{overview.goal_path.goal.title}”"
        console.print(Rule(f"[muted]{heading}[/muted]", style="muted", align="left"))
        _print_next_modules(overview.next_modules)
    console.print(Rule("[muted]trilhas[/muted]", style="muted", align="left"))
    _print_track_progress(overview.tracks)


def checkin(
    intention: str = typer.Option(
        None, "--intention", "-i", help="O que você vai estudar hoje, em uma frase."
    ),
) -> None:
    with challenges_as_exit(), open_workspace() as workspace:
        if intention is None:
            intention = typer.prompt("O que você vai estudar hoje?")
        today_date = local_today()
        check_in(workspace.conn, workspace.user_id, intention, today_date, utc_now())
        streak = get_streak(workspace.conn, workspace.user_id, today_date)
    say_ok(checkin_saved_message(streak))


def tracks() -> None:
    with challenges_as_exit(), open_workspace() as workspace:
        track_views = list_track_views(workspace.conn, workspace.user_id)
    if not track_views:
        console.print("Nenhuma trilha carregada. Rode [accent]hone content sync[/accent].")
        return
    _print_track_progress(track_views)
    console.print("\nDetalhes: [accent]hone track <trilha>[/accent]")


def track(
    slug: str = typer.Argument(..., help="Identificador da trilha (ex.: cs-fundamentals)."),
) -> None:
    with challenges_as_exit(), open_workspace() as workspace:
        view = find_track_view(workspace.conn, workspace.user_id, slug)
    if view is None:
        console.print(f"[challenge]Desafio:[/challenge] não achei a trilha “{slug}”.")
        console.print(
            "[muted]Próximo passo:[/muted] veja as trilhas com [accent]hone tracks[/accent]."
        )
        raise typer.Exit(code=1)

    console.print(
        f"[title]{view.name}[/title]  {progress_bar(view.completed_count, view.total_count)}"
    )
    console.print(f"[muted]{view.description}[/muted]\n")
    for module in view.modules:
        console.print(
            f"{status_marker(module.status)} [bold]{module.position}. {module.title}[/bold]  "
            f"{status_label(module.status)}  [muted]{module.slug}[/muted]"
        )
        if module.missing_prerequisites:
            missing = ", ".join(link.title for link in module.missing_prerequisites)
            console.print(f"    [muted]precisa de: {missing}[/muted]")
    console.print("\nPara estudar: [accent]hone read <módulo>[/accent]")


def read(
    module: str = typer.Argument(
        ..., help="Módulo a abrir (ex.: recursion ou cs-fundamentals/recursion)."
    ),
) -> None:
    with challenges_as_exit(), open_workspace() as workspace:
        target = resolve_module(workspace.conn, workspace.user_id, module)
        start_module(workspace.conn, workspace.user_id, target, utc_now())
        text = read_module_content(workspace.settings.content_dir, target.content_path or "")

    console.print(Markdown(text))
    console.print(Rule(style="muted"))
    console.print(
        f"Respondeu a recuperação ativa sem olhar? Então: [accent]hone done {target.key}[/accent]"
    )


def done(module: str = typer.Argument(..., help="Módulo concluído (ex.: recursion).")) -> None:
    with challenges_as_exit(), open_workspace() as workspace:
        target = resolve_module(workspace.conn, workspace.user_id, module)
        already_completed = target.status is ModuleStatus.COMPLETED
        unlocked = complete_module(workspace.conn, workspace.user_id, target, utc_now())
        track_view = find_track_view(workspace.conn, workspace.user_id, target.track_slug)

    if already_completed:
        console.print(f"[muted]“{target.title}” já estava concluído.[/muted]")
        return

    say_ok(module_completed_message(target.title))
    if unlocked:
        console.print("Destravou:")
        _print_next_modules(unlocked)
    if track_view is not None and track_view.is_complete:
        console.print(f"\n[title]{track_completed_message(track_view.name)}[/title]")
