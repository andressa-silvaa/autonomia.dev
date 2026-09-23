from __future__ import annotations

import sqlite3

from formacao.core.models import User


class UserNotFoundError(Exception):
    pass


def _row_to_user(row: sqlite3.Row) -> User:
    return User(id=row["id"], name=row["name"], created_at=row["created_at"])


def find_primary_user(conn: sqlite3.Connection) -> User | None:
    row = conn.execute("SELECT id, name, created_at FROM users ORDER BY id LIMIT 1").fetchone()
    return _row_to_user(row) if row is not None else None


def get_primary_user(conn: sqlite3.Connection) -> User:
    user = find_primary_user(conn)
    if user is None:
        raise UserNotFoundError("No user registered. Run `formacao db init` first.")
    return user


def ensure_default_user(conn: sqlite3.Connection, name: str) -> tuple[User, bool]:
    existing = find_primary_user(conn)
    if existing is not None:
        return existing, False

    with conn:
        cursor = conn.execute("INSERT INTO users (name) VALUES (?)", (name,))
    created = conn.execute(
        "SELECT id, name, created_at FROM users WHERE id = ?", (cursor.lastrowid,)
    ).fetchone()
    return _row_to_user(created), True
