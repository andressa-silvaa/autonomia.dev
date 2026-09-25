from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from hone.core.db import (
    MigrationError,
    connect,
    discover_migrations,
    latest_version,
    migrate,
    schema_version,
    table_counts,
)
from hone.core.models import Mastery
from hone.core.users import ensure_default_user

EXPECTED_TABLES = {
    "users",
    "areas",
    "competencies",
    "tracks",
    "modules",
    "module_prerequisites",
    "module_competencies",
    "exercises",
    "projects",
    "user_competencies",
    "study_sessions",
    "attempts",
    "reviews",
    "module_progress",
    "checkins",
    "diagnostic_questions",
    "diagnostic_runs",
    "diagnostic_answers",
    "mastery_events",
    "user_goals",
    "exercise_progress",
    "xp_events",
}


def test_migrate_creates_all_tables(conn: sqlite3.Connection) -> None:
    assert set(table_counts(conn)) == EXPECTED_TABLES
    assert schema_version(conn) == latest_version()


def test_migrate_is_idempotent(conn: sqlite3.Connection) -> None:
    assert migrate(conn) == []


def test_failed_migration_rolls_back(tmp_path: Path) -> None:
    migrations = tmp_path / "migrations"
    migrations.mkdir()
    (migrations / "0001_ok.sql").write_text("CREATE TABLE a (id INTEGER);", encoding="utf-8")
    (migrations / "0002_broken.sql").write_text(
        "CREATE TABLE b (id INTEGER);\nTHIS IS NOT SQL;", encoding="utf-8"
    )
    connection = connect(tmp_path / "x.db")
    with pytest.raises(MigrationError, match="0002_broken.sql"):
        migrate(connection, migrations)

    assert schema_version(connection) == 1
    assert set(table_counts(connection)) == {"a"}
    connection.close()


def test_gap_in_numbering_is_rejected(tmp_path: Path) -> None:
    (tmp_path / "0001_a.sql").write_text("", encoding="utf-8")
    (tmp_path / "0003_c.sql").write_text("", encoding="utf-8")
    with pytest.raises(MigrationError, match="expected 0002"):
        discover_migrations(tmp_path)


def test_invalid_filename_is_rejected(tmp_path: Path) -> None:
    (tmp_path / "1_no_padding.sql").write_text("", encoding="utf-8")
    with pytest.raises(MigrationError, match="Invalid migration filename"):
        discover_migrations(tmp_path)


def test_database_newer_than_code_is_rejected(conn: sqlite3.Connection) -> None:
    conn.execute(f"PRAGMA user_version = {latest_version() + 1}")
    with pytest.raises(MigrationError, match="only knows up to"):
        migrate(conn)


def _make_module(conn: sqlite3.Connection) -> int:
    track_id = conn.execute("INSERT INTO tracks (slug, name) VALUES ('t', 'Track')").lastrowid
    return conn.execute(
        "INSERT INTO modules (track_id, slug, title) VALUES (?, 'm1', 'Module 1')", (track_id,)
    ).lastrowid


def test_foreign_keys_are_enforced(conn: sqlite3.Connection) -> None:
    with pytest.raises(sqlite3.IntegrityError, match="FOREIGN KEY"):
        conn.execute("INSERT INTO modules (track_id, slug, title) VALUES (999, 'x', 'X')")


def test_module_cannot_require_itself(conn: sqlite3.Connection) -> None:
    module_id = _make_module(conn)
    with pytest.raises(sqlite3.IntegrityError, match="CHECK"):
        conn.execute(
            "INSERT INTO module_prerequisites (module_id, prerequisite_id) VALUES (?, ?)",
            (module_id, module_id),
        )


def test_schema_accepts_exactly_the_mastery_enum(conn: sqlite3.Connection) -> None:
    user, _ = ensure_default_user(conn, "Tester")
    area_id = conn.execute("INSERT INTO areas (slug, name) VALUES ('a', 'A')").lastrowid
    competency_id = conn.execute(
        "INSERT INTO competencies (area_id, slug, name) VALUES (?, 'c', 'C')", (area_id,)
    ).lastrowid

    for state in Mastery:
        conn.execute(
            "INSERT OR REPLACE INTO user_competencies (user_id, competency_id, mastery) "
            "VALUES (?, ?, ?)",
            (user.id, competency_id, state),
        )
    with pytest.raises(sqlite3.IntegrityError, match="CHECK"):
        conn.execute(
            "INSERT OR REPLACE INTO user_competencies (user_id, competency_id, mastery) "
            "VALUES (?, ?, 'expert')",
            (user.id, competency_id),
        )


def test_mastery_is_ordered() -> None:
    assert Mastery.NOT_STUDIED.rank == 0
    assert Mastery.MASTERY.rank == len(Mastery) - 1
    assert Mastery.CAN_APPLY.rank < Mastery.CAN_EXPLAIN.rank
    assert Mastery.CAN_APPLY.label == "consegue aplicar"


def test_attempt_score_must_be_between_0_and_1(conn: sqlite3.Connection) -> None:
    user, _ = ensure_default_user(conn, "Tester")
    module_id = _make_module(conn)
    exercise_id = conn.execute(
        "INSERT INTO exercises (module_id, slug, title, kind, grading, prompt) "
        "VALUES (?, 'e', 'E', 'quiz', 'auto', '?')",
        (module_id,),
    ).lastrowid
    with pytest.raises(sqlite3.IntegrityError, match="CHECK"):
        conn.execute(
            "INSERT INTO attempts (user_id, exercise_id, score) VALUES (?, ?, 1.5)",
            (user.id, exercise_id),
        )


def test_ensure_default_user_creates_only_once(conn: sqlite3.Connection) -> None:
    first, created_first = ensure_default_user(conn, "Andressa")
    second, created_second = ensure_default_user(conn, "Another name")
    assert (created_first, created_second) == (True, False)
    assert second.id == first.id
    assert second.name == "Andressa"
