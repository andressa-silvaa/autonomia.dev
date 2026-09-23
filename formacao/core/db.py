from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path

MIGRATIONS_DIR = Path(__file__).parent / "migrations"

_MIGRATION_FILENAME = re.compile(r"^(\d{4})_([a-z0-9_]+)\.sql$")


class MigrationError(Exception):
    pass


@dataclass(frozen=True, slots=True)
class Migration:
    version: int
    name: str
    path: Path


def connect(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


def discover_migrations(directory: Path = MIGRATIONS_DIR) -> list[Migration]:
    migrations: list[Migration] = []
    for path in sorted(directory.glob("*.sql")):
        match = _MIGRATION_FILENAME.match(path.name)
        if match is None:
            raise MigrationError(
                f"Invalid migration filename: {path.name!r} (expected NNNN_description.sql)"
            )
        migrations.append(Migration(int(match[1]), match[2], path))

    for expected, migration in enumerate(migrations, start=1):
        if migration.version != expected:
            raise MigrationError(
                f"Broken migration numbering: expected {expected:04d}, found {migration.path.name}"
            )
    return migrations


def latest_version(directory: Path = MIGRATIONS_DIR) -> int:
    migrations = discover_migrations(directory)
    return migrations[-1].version if migrations else 0


def schema_version(conn: sqlite3.Connection) -> int:
    return conn.execute("PRAGMA user_version").fetchone()[0]


def _apply_in_transaction(conn: sqlite3.Connection, migration: Migration) -> None:
    sql = migration.path.read_text(encoding="utf-8")
    script = f"BEGIN;\n{sql}\nPRAGMA user_version = {migration.version};\nCOMMIT;"
    try:
        conn.executescript(script)
    except sqlite3.Error as exc:
        if conn.in_transaction:
            conn.rollback()
        raise MigrationError(f"Failed to apply {migration.path.name}: {exc}") from exc


def migrate(conn: sqlite3.Connection, directory: Path = MIGRATIONS_DIR) -> list[Migration]:
    migrations = discover_migrations(directory)
    current = schema_version(conn)
    latest = migrations[-1].version if migrations else 0

    if current > latest:
        raise MigrationError(
            f"Database is at version {current}, but the code only knows up to {latest}. "
            "Update the code before using this database."
        )

    pending = [migration for migration in migrations if migration.version > current]
    for migration in pending:
        _apply_in_transaction(conn, migration)
    return pending


def _quote_identifier(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def table_counts(conn: sqlite3.Connection) -> dict[str, int]:
    table_names = [
        row["name"]
        for row in conn.execute(
            "SELECT name FROM sqlite_master "
            "WHERE type = 'table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
        )
    ]
    return {
        name: conn.execute(f"SELECT COUNT(*) FROM {_quote_identifier(name)}").fetchone()[0]
        for name in table_names
    }
