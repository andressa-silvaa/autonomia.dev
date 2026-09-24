from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from pathlib import Path

import pytest

from hone.core.db import connect, migrate
from hone.core.users import ensure_default_user
from hone.engines.content import load_content, sync_content
from tests.content_builder import write_content


@pytest.fixture
def content_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    root = write_content(tmp_path / "content")
    monkeypatch.setenv("HONE_CONTENT_DIR", str(root))
    return root


@pytest.fixture
def db_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    path = tmp_path / "test.db"
    monkeypatch.setenv("HONE_DB_PATH", str(path))
    monkeypatch.setenv("HONE_USER_NAME", "Tester")
    return path


@pytest.fixture
def conn(db_path: Path) -> Iterator[sqlite3.Connection]:
    connection = connect(db_path)
    migrate(connection)
    yield connection
    connection.close()


@pytest.fixture
def user_id(conn: sqlite3.Connection) -> int:
    user, _ = ensure_default_user(conn, "Tester")
    assert user.id is not None
    return user.id


@pytest.fixture
def synced(conn: sqlite3.Connection, content_dir: Path, user_id: int) -> sqlite3.Connection:
    sync_content(conn, load_content(content_dir))
    return conn
