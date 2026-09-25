from __future__ import annotations

from contextlib import closing
from dataclasses import dataclass

from hone.config import Settings
from hone.core.db import Migration, connect, migrate
from hone.core.users import ensure_default_user
from hone.engines.content import SyncReport, load_content, sync_content


@dataclass(frozen=True, slots=True)
class StartupReport:
    user_name: str
    first_run: bool
    applied_migrations: tuple[Migration, ...]
    sync: SyncReport


def prepare_system(settings: Settings) -> StartupReport:
    content = load_content(settings.content_dir, settings.exercises_dir)
    with closing(connect(settings.db_path)) as conn:
        applied = migrate(conn)
        user, created = ensure_default_user(conn, settings.user_name)
        report = sync_content(conn, content)
    return StartupReport(user.name, created, tuple(applied), report)
