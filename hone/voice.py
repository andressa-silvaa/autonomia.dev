from __future__ import annotations

import sqlite3
from dataclasses import dataclass

from hone.core.users import UserNotFoundError
from hone.core.workspace import DatabaseMissingError, SchemaOutdatedError
from hone.engines.checkins import AlreadyCheckedInError, EmptyIntentionError, Streak
from hone.engines.content import ContentError, ContentFileMissingError
from hone.engines.progress import (
    AmbiguousModuleError,
    ModuleLink,
    ModuleLockedError,
    ModuleStatus,
    UnknownModuleError,
)
from hone.engines.sessions import ActiveSessionExistsError, NoActiveSessionError

MODULE_STATUS_LABELS = {
    ModuleStatus.LOCKED: "trancado",
    ModuleStatus.AVAILABLE: "disponível",
    ModuleStatus.IN_PROGRESS: "estudando",
    ModuleStatus.COMPLETED: "concluído",
}


def streak_message(streak: Streak) -> str:
    if streak.current == 0:
        if streak.longest > 0:
            return (
                f"Streak zerado. Seu recorde é {streak.longest} dias, "
                "e recomeçar também é disciplina."
            )
        return (
            "Nenhum dia no placar ainda. O primeiro check-in é o mais difícil, e o mais importante."
        )
    if not streak.checked_in_today:
        return f"Seu streak de {streak.current} dias está esperando o check-in de hoje."
    if streak.current == 1:
        return "Dia 1. Todo streak que vale a pena começou exatamente assim."
    if streak.current == streak.longest and streak.current >= 3:
        return (
            f"{streak.current} dias seguidos. "
            "Recorde pessoal, e ninguém te deu isso: você construiu."
        )
    if streak.current >= 7:
        return f"{streak.current} dias seguidos. Isso já é hábito, não sorte."
    return f"{streak.current} dias seguidos. Continua, que está funcionando."


def checkin_saved_message(streak: Streak) -> str:
    if streak.current == 1:
        return "Check-in feito. Hoje conta."
    return f"Check-in feito. {streak.current} dias seguidos, e o de hoje também é seu."


def module_completed_message(title: str) -> str:
    return f"Você venceu “{title}”. Não foi sorte, foi estudo."


def track_completed_message(track_name: str) -> str:
    return f"Trilha {track_name} completa. Olha até onde você chegou sem pedir licença."


def session_stopped_message(minutes: int) -> str:
    if minutes < 1:
        return "Sessão encerrada. Curtinha, mas aparecer já é metade do caminho."
    if minutes < 25:
        return (
            f"Sessão encerrada: {minutes} min. "
            "Pouco tempo bem usado vale mais que muito tempo disperso."
        )
    return f"Sessão encerrada: {minutes} min de foco de verdade."


@dataclass(frozen=True, slots=True)
class Challenge:
    problem: str
    next_step: str


def _module_list(links: tuple[ModuleLink, ...]) -> str:
    return ", ".join(f"{link.title} ({link.key})" for link in links)


def _challenge_for_module_error(error: Exception) -> Challenge | None:
    match error:
        case UnknownModuleError():
            return Challenge(
                f"não achei o módulo “{error.reference}”.",
                "veja os nomes certinhos com [accent]hone track <trilha>[/accent].",
            )
        case AmbiguousModuleError():
            return Challenge(
                f"“{error.reference}” existe em mais de uma trilha.",
                f"use o nome completo: {', '.join(error.candidates)}.",
            )
        case ModuleLockedError():
            return Challenge(
                f"“{error.module.title}” ainda está trancado.",
                f"conclua antes: {_module_list(error.module.missing_prerequisites)}.",
            )
    return None


def _challenge_for_study_error(error: Exception) -> Challenge | None:
    match error:
        case ActiveSessionExistsError():
            topic = f" em {error.session.module_title}" if error.session.module_title else ""
            return Challenge(
                f"já tem uma sessão rolando{topic}.",
                "encerre com [accent]hone session stop[/accent] antes de abrir outra.",
            )
        case NoActiveSessionError():
            return Challenge(
                "não tem nenhuma sessão aberta agora.",
                "comece uma com [accent]hone session start[/accent].",
            )
        case AlreadyCheckedInError():
            return Challenge(
                f"o check-in de hoje já está feito: “{error.checkin.intention}”.",
                "agora é estudar. Amanhã tem outro.",
            )
        case EmptyIntentionError():
            return Challenge(
                "check-in sem intenção não vale.",
                "escreva em uma frase o que você vai estudar hoje.",
            )
    return None


def _challenge_for_setup_error(error: Exception) -> Challenge | None:
    match error:
        case DatabaseMissingError():
            return Challenge(
                f"ainda não existe banco em {error.db_path}.",
                "rode [accent]hone db init[/accent].",
            )
        case SchemaOutdatedError():
            return Challenge(
                f"o banco está na versão {error.current}, e o código já espera a {error.latest}.",
                "rode [accent]hone db init[/accent] para atualizar (seus dados continuam lá).",
            )
        case UserNotFoundError():
            return Challenge(
                "o banco existe, mas ninguém está cadastrado nele.",
                "rode [accent]hone db init[/accent].",
            )
        case ContentError():
            return Challenge(
                "o conteúdo das trilhas tem problemas:\n"
                + "\n".join(f"  - {p}" for p in error.problems),
                "corrija os arquivos em data/ e rode [accent]hone content sync[/accent] de novo.",
            )
        case ContentFileMissingError():
            return Challenge(
                "o arquivo de conteúdo desse módulo sumiu.",
                "confira data/tracks/ e rode [accent]hone content sync[/accent].",
            )
        case sqlite3.Error() | OSError():
            return Challenge(
                f"não consegui acessar o banco ({error}).",
                "confira HONE_DB_PATH no .env e se você tem permissão de escrita na pasta.",
            )
    return None


def challenge_for(error: Exception) -> Challenge | None:
    for describe in (
        _challenge_for_module_error,
        _challenge_for_study_error,
        _challenge_for_setup_error,
    ):
        challenge = describe(error)
        if challenge is not None:
            return challenge
    return None
