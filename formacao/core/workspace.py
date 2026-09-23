from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

from formacao.config import Settings, load_settings
from formacao.core.db import connect, latest_version, schema_version
from formacao.core.models import User
from formacao.core.users import get_primary_user


class DatabaseMissingError(Exception):
    def __init__(self, db_path: Path) -> None:
        super().__init__(f"Database not found at {db_path}")
        self.db_path = db_path


class SchemaOutdatedError(Exception):
    def __init__(self, current: int, latest: int) -> None:
        super().__init__(f"Database schema is at version {current}, code expects {latest}")
        self.current = current
        self.latest = latest


@dataclass(frozen=True, slots=True)
class Workspace:
    settings: Settings
    conn: sqlite3.Connection
    user: User

    @property
    def user_id(self) -> int:
        assert self.user.id is not None
        return self.user.id


@contextmanager
def open_workspace(
    settings: Settings | None = None, *, allow_cross_thread: bool = False
) -> Iterator[Workspace]:
    settings = settings or load_settings()
    if not settings.db_path.exists():
        raise DatabaseMissingError(settings.db_path)

    conn = connect(settings.db_path, allow_cross_thread=allow_cross_thread)
    try:
        current, latest = schema_version(conn), latest_version()
        if current < latest:
            raise SchemaOutdatedError(current, latest)
        yield Workspace(settings, conn, get_primary_user(conn))
    finally:
        conn.close()
