from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from hone.api.app import app as api_app
from hone.config import load_settings
from hone.core.db import connect, migrate
from hone.core.users import ensure_default_user
from hone.engines.content import load_content, sync_content
from hone.startup import prepare_system
from tests.content_builder import write_content, write_exercises

UNREACHABLE_OLLAMA_URL = "http://127.0.0.1:9"
API_BASE_URL = "http://127.0.0.1"
CLIENT_HEADERS = {"X-Hone-Client": "dashboard"}


@pytest.fixture(autouse=True)
def isolated_settings(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HONE_WORKSPACE_DIR", str(tmp_path / "workspace"))
    monkeypatch.setenv("HONE_OLLAMA_URL", UNREACHABLE_OLLAMA_URL)
    monkeypatch.setenv("HONE_EXERCISES_DIR", str(tmp_path / "no-exercises"))


@pytest.fixture
def content_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    root = write_content(tmp_path / "content")
    monkeypatch.setenv("HONE_CONTENT_DIR", str(root))
    return root


@pytest.fixture
def exercises_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    root = write_exercises(tmp_path / "exercises")
    monkeypatch.setenv("HONE_EXERCISES_DIR", str(root))
    return root


@pytest.fixture
def workspace_dir(tmp_path: Path) -> Path:
    return tmp_path / "workspace"


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


@pytest.fixture
def synced_with_exercises(
    conn: sqlite3.Connection, content_dir: Path, exercises_dir: Path, user_id: int
) -> sqlite3.Connection:
    sync_content(conn, load_content(content_dir, exercises_dir))
    return conn


@pytest.fixture
def client(db_path: Path, content_dir: Path, exercises_dir: Path) -> TestClient:
    prepare_system(load_settings())
    return TestClient(api_app, base_url=API_BASE_URL, headers=CLIENT_HEADERS)
