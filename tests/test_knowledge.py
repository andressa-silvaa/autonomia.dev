from __future__ import annotations

import sqlite3
from datetime import UTC, date, datetime

import pytest

from hone.core.models import Mastery
from hone.engines.knowledge import (
    NoGoalError,
    build_knowledge_map,
    build_learning_path,
    clear_goal,
    find_goal,
    get_goal_path,
    list_assessed_gaps,
    list_module_levels,
    set_goal,
)
from hone.engines.mastery import record_mastery
from hone.engines.overview import build_overview
from hone.engines.progress import complete_module, resolve_module

NOW = datetime(2026, 9, 24, 12, 0, tzinfo=UTC)


def _set_mastery(conn: sqlite3.Connection, user_id: int, slug: str, mastery: Mastery) -> None:
    competency_id = conn.execute("SELECT id FROM competencies WHERE slug = ?", (slug,)).fetchone()
    with conn:
        record_mastery(conn, user_id, competency_id[0], mastery, "test", None, NOW)


def _complete(conn: sqlite3.Connection, user_id: int, slug: str) -> None:
    complete_module(conn, user_id, resolve_module(conn, user_id, slug), NOW)


def _path_to(conn: sqlite3.Connection, user_id: int, slug: str):
    return build_learning_path(conn, user_id, resolve_module(conn, user_id, slug))


def test_knowledge_map_groups_competencies_by_area(
    synced: sqlite3.Connection, user_id: int
) -> None:
    _set_mastery(synced, user_id, "basics", Mastery.RECOGNIZES)
    areas = build_knowledge_map(synced, user_id)
    assert [area.slug for area in areas] == ["fundamentals"]
    states = {state.slug: state for state in areas[0].competencies}
    assert states["basics"].mastery is Mastery.RECOGNIZES
    assert states["basics"].module_keys == ("sample/first",)
    assert states["advanced"].mastery is Mastery.NOT_STUDIED


def test_module_levels_follow_prerequisite_depth(synced: sqlite3.Connection, user_id: int) -> None:
    levels = list_module_levels(synced, user_id)
    assert [[module.slug for module in level] for level in levels] == [
        ["first"],
        ["second"],
        ["third"],
    ]


def test_path_lists_missing_prerequisites_in_study_order(
    synced: sqlite3.Connection, user_id: int
) -> None:
    path = _path_to(synced, user_id, "third")
    assert [step.module.slug for step in path.steps] == ["first", "second", "third"]
    assert [state.slug for state in path.gaps] == ["basics", "advanced"]
    assert path.next_step is not None and path.next_step.module.slug == "first"
    assert not path.is_reached


def test_path_flags_what_the_diagnostic_says_is_already_known(
    synced: sqlite3.Connection, user_id: int
) -> None:
    _set_mastery(synced, user_id, "basics", Mastery.CAN_APPLY)
    path = _path_to(synced, user_id, "third")
    known = {step.module.slug: step.likely_known for step in path.steps}
    assert known == {"first": True, "second": False, "third": False}
    assert [state.slug for state in path.gaps] == ["advanced"]


def test_completed_modules_leave_the_path_but_fragile_ones_stay_as_gaps(
    synced: sqlite3.Connection, user_id: int
) -> None:
    _complete(synced, user_id, "first")
    path = _path_to(synced, user_id, "third")
    assert [step.module.slug for step in path.steps] == ["second", "third"]
    assert [state.slug for state in path.gaps] == ["advanced"]

    _set_mastery(synced, user_id, "basics", Mastery.UNKNOWN)
    path = _path_to(synced, user_id, "third")
    assert [state.slug for state in path.gaps] == ["basics", "advanced"]


def test_reached_goal_has_no_steps(synced: sqlite3.Connection, user_id: int) -> None:
    _complete(synced, user_id, "first")
    path = _path_to(synced, user_id, "first")
    assert path.is_reached
    assert path.steps == ()
    assert path.next_step is None


def test_goal_can_be_set_replaced_and_cleared(synced: sqlite3.Connection, user_id: int) -> None:
    with pytest.raises(NoGoalError):
        get_goal_path(synced, user_id)

    set_goal(synced, user_id, resolve_module(synced, user_id, "second"), NOW)
    set_goal(synced, user_id, resolve_module(synced, user_id, "third"), NOW)
    goal = find_goal(synced, user_id)
    assert goal is not None and goal.slug == "third"
    assert get_goal_path(synced, user_id).goal.slug == "third"

    clear_goal(synced, user_id)
    assert find_goal(synced, user_id) is None


def test_assessed_gaps_ignore_what_was_never_studied(
    synced: sqlite3.Connection, user_id: int
) -> None:
    assert list_assessed_gaps(synced, user_id) == []
    _set_mastery(synced, user_id, "advanced", Mastery.BEGINNING)
    _set_mastery(synced, user_id, "basics", Mastery.CAN_APPLY)
    assert [state.slug for state in list_assessed_gaps(synced, user_id)] == ["advanced"]


def test_overview_suggests_modules_from_the_goal_path(
    synced: sqlite3.Connection, user_id: int
) -> None:
    track_id = synced.execute("SELECT id FROM tracks WHERE slug = 'sample'").fetchone()[0]
    synced.execute(
        "INSERT INTO modules (track_id, slug, title, position) VALUES (?, 'side', 'Desvio', 0)",
        (track_id,),
    )
    today = date(2026, 9, 24)

    without_goal = build_overview(synced, user_id, today, NOW)
    assert [module.slug for module in without_goal.next_modules] == ["side", "first"]

    set_goal(synced, user_id, resolve_module(synced, user_id, "second"), NOW)
    with_goal = build_overview(synced, user_id, today, NOW)
    assert [module.slug for module in with_goal.next_modules] == ["first"]
    assert with_goal.goal_path is not None and with_goal.goal_path.goal.slug == "second"
