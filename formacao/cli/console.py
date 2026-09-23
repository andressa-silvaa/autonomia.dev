from __future__ import annotations

import sys

from rich.console import Console
from rich.theme import Theme

from formacao.ui_palette import RICH_STYLES


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
