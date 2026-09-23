from __future__ import annotations

import sqlite3

from formacao.core.models import User


def _row_to_user(row: sqlite3.Row) -> User:
    return User(id=row["id"], name=row["name"], created_at=row["created_at"])


def ensure_default_user(conn: sqlite3.Connection, name: str) -> tuple[User, bool]:
    existing = conn.execute("SELECT id, name, created_at FROM users ORDER BY id LIMIT 1").fetchone()
    if existing is not None:
        return _row_to_user(existing), False

    with conn:
        cursor = conn.execute("INSERT INTO users (name) VALUES (?)", (name,))
    created = conn.execute(
        "SELECT id, name, created_at FROM users WHERE id = ?", (cursor.lastrowid,)
    ).fetchone()
    return _row_to_user(created), True
