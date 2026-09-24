from __future__ import annotations

import sys
from collections.abc import Iterator
from contextlib import contextmanager

import typer
from rich.console import Console
from rich.theme import Theme

from hone.core.models import Mastery
from hone.engines.progress import ModuleStatus
from hone.ui_palette import RICH_STYLES
from hone.voice import MODULE_STATUS_LABELS, challenge_for

PROGRESS_BAR_WIDTH = 20
FILLED_BAR = "━"
EMPTY_BAR = "─"
FILLED_MASTERY = "●"
EMPTY_MASTERY = "○"
MASTERY_METER_WIDTH = len(Mastery) - 1

STATUS_MARKERS = {
    ModuleStatus.COMPLETED: "[ok]✔[/ok]",
    ModuleStatus.IN_PROGRESS: "[accent]▶[/accent]",
    ModuleStatus.AVAILABLE: "[secondary]○[/secondary]",
    ModuleStatus.LOCKED: "[muted]·[/muted]",
}


def _force_utf8_output() -> None:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")


_force_utf8_output()
console = Console(theme=Theme(RICH_STYLES))


def say_ok(message: str) -> None:
    console.print(f"[ok]✔[/ok] {message}")


def say_challenge(problem: str, next_step: str) -> None:
    console.print(f"[challenge]Desafio:[/challenge] {problem}")
    console.print(f"[muted]Próximo passo:[/muted] {next_step}")


@contextmanager
def challenges_as_exit() -> Iterator[None]:
    try:
        yield
    except Exception as error:
        challenge = challenge_for(error)
        if challenge is None:
            raise
        say_challenge(challenge.problem, challenge.next_step)
        raise typer.Exit(code=1) from error


def progress_bar(done: int, total: int, width: int = PROGRESS_BAR_WIDTH) -> str:
    filled = round(width * done / total) if total else 0
    return f"[accent]{FILLED_BAR * filled}[/accent][muted]{EMPTY_BAR * (width - filled)}[/muted]"


def status_marker(status: ModuleStatus) -> str:
    return STATUS_MARKERS[status]


def status_label(status: ModuleStatus) -> str:
    style = "muted" if status is ModuleStatus.LOCKED else "secondary"
    return f"[{style}]{MODULE_STATUS_LABELS[status]}[/{style}]"


def mastery_meter(mastery: Mastery) -> str:
    filled = mastery.rank
    return (
        f"[accent]{FILLED_MASTERY * filled}[/accent]"
        f"[muted]{EMPTY_MASTERY * (MASTERY_METER_WIDTH - filled)}[/muted]"
    )


def mastery_label(mastery: Mastery) -> str:
    if mastery is Mastery.NOT_STUDIED:
        style = "muted"
    elif mastery.rank >= Mastery.CAN_APPLY.rank:
        style = "ok"
    elif mastery is Mastery.UNKNOWN:
        style = "warning"
    else:
        style = "secondary"
    return f"[{style}]{mastery.label}[/{style}]"
