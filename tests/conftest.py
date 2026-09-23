from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from pathlib import Path

import pytest

from formacao.core.db import connect, migrate


@pytest.fixture
def db_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    path = tmp_path / "test.db"
    monkeypatch.setenv("FORMACAO_DB_PATH", str(path))
    monkeypatch.setenv("FORMACAO_USER_NAME", "Tester")
    return path


@pytest.fixture
def conn(db_path: Path) -> Iterator[sqlite3.Connection]:
    connection = connect(db_path)
    migrate(connection)
    yield connection
    connection.close()
