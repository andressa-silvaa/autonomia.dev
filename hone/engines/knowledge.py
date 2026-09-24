from __future__ import annotations

import sqlite3
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime

import networkx as nx

from hone.core.clock import to_iso_utc
from hone.core.models import Mastery
from hone.engines.content import module_key
from hone.engines.progress import ModuleStatus, ModuleView, list_module_views

SOLID_MASTERY = Mastery.CAN_APPLY


class NoGoalError(Exception):
    def __init__(self) -> None:
        super().__init__("No learning goal set")


@dataclass(frozen=True, slots=True)
class CompetencyState:
    id: int
    slug: str
    name: str
    area_slug: str
    mastery: Mastery
    module_keys: tuple[str, ...]

    @property
    def is_solid(self) -> bool:
        return self.mastery.rank >= SOLID_MASTERY.rank

    @property
    def was_assessed(self) -> bool:
        return self.mastery is not Mastery.NOT_STUDIED


@dataclass(frozen=True, slots=True)
class AreaMap:
    slug: str
    name: str
    competencies: tuple[CompetencyState, ...]


@dataclass(frozen=True, slots=True)
class PathStep:
    module: ModuleView
    competencies: tuple[CompetencyState, ...]

    @property
    def likely_known(self) -> bool:
        return bool(self.competencies) and all(state.is_solid for state in self.competencies)


@dataclass(frozen=True, slots=True)
class LearningPath:
    goal: ModuleView
    steps: tuple[PathStep, ...]
    gaps: tuple[CompetencyState, ...]

    @property
    def is_reached(self) -> bool:
        return self.goal.status is ModuleStatus.COMPLETED

    @property
    def next_step(self) -> PathStep | None:
        return next((step for step in self.steps if step.module.is_open), None)


def list_competency_states(conn: sqlite3.Connection, user_id: int) -> list[CompetencyState]:
    module_keys: dict[int, list[str]] = defaultdict(list)
    for row in conn.execute(
        "SELECT module_competencies.competency_id, tracks.slug AS track_slug, "
        "modules.slug AS module_slug FROM module_competencies "
        "JOIN modules ON modules.id = module_competencies.module_id "
        "JOIN tracks ON tracks.id = modules.track_id "
        "ORDER BY tracks.name, modules.position"
    ):
        module_keys[row["competency_id"]].append(module_key(row["track_slug"], row["module_slug"]))

    rows = conn.execute(
        "SELECT competencies.id, competencies.slug, competencies.name, areas.slug AS area_slug, "
        "user_competencies.mastery FROM competencies "
        "JOIN areas ON areas.id = competencies.area_id "
        "LEFT JOIN user_competencies ON user_competencies.competency_id = competencies.id "
        "AND user_competencies.user_id = ? "
        "ORDER BY areas.id, competencies.id",
        (user_id,),
    )
    return [
        CompetencyState(
            id=row["id"],
            slug=row["slug"],
            name=row["name"],
            area_slug=row["area_slug"],
            mastery=Mastery(row["mastery"] or Mastery.NOT_STUDIED),
            module_keys=tuple(module_keys[row["id"]]),
        )
        for row in rows
    ]


def build_knowledge_map(conn: sqlite3.Connection, user_id: int) -> list[AreaMap]:
    states_by_area: dict[str, list[CompetencyState]] = defaultdict(list)
    for state in list_competency_states(conn, user_id):
        states_by_area[state.area_slug].append(state)

    return [
        AreaMap(row["slug"], row["name"], tuple(states_by_area[row["slug"]]))
        for row in conn.execute("SELECT slug, name FROM areas ORDER BY id")
        if states_by_area[row["slug"]]
    ]


def build_module_graph(modules: list[ModuleView]) -> nx.DiGraph:
    graph = nx.DiGraph()
    for module in modules:
        graph.add_node(module.key, module=module)
    for module in modules:
        for prerequisite in module.prerequisites:
            graph.add_edge(prerequisite.key, module.key)
    return graph


def _study_order(graph: nx.DiGraph, keys: set[str]) -> list[ModuleView]:
    subgraph = graph.subgraph(keys)
    ordered_keys = nx.lexicographical_topological_sort(
        subgraph, key=lambda key: (graph.nodes[key]["module"].position, key)
    )
    return [graph.nodes[key]["module"] for key in ordered_keys]


def list_module_levels(conn: sqlite3.Connection, user_id: int) -> list[list[ModuleView]]:
    graph = build_module_graph(list_module_views(conn, user_id))
    return [
        sorted(
            (graph.nodes[key]["module"] for key in generation),
            key=lambda module: (module.position, module.key),
        )
        for generation in nx.topological_generations(graph)
    ]


def _counts_as_gap(state: CompetencyState, module: ModuleView) -> bool:
    if state.is_solid:
        return False
    if module.status is ModuleStatus.COMPLETED:
        return state.was_assessed
    return True


def build_learning_path(conn: sqlite3.Connection, user_id: int, goal: ModuleView) -> LearningPath:
    graph = build_module_graph(list_module_views(conn, user_id))
    states_by_module: dict[str, list[CompetencyState]] = defaultdict(list)
    for state in list_competency_states(conn, user_id):
        for key in state.module_keys:
            states_by_module[key].append(state)

    route = _study_order(graph, nx.ancestors(graph, goal.key) | {goal.key})
    steps = tuple(
        PathStep(module, tuple(states_by_module[module.key]))
        for module in route
        if module.status is not ModuleStatus.COMPLETED
    )

    gaps: dict[int, CompetencyState] = {}
    for module in route:
        for state in states_by_module[module.key]:
            if _counts_as_gap(state, module):
                gaps.setdefault(state.id, state)

    return LearningPath(goal, steps, tuple(gaps.values()))


def list_assessed_gaps(conn: sqlite3.Connection, user_id: int) -> list[CompetencyState]:
    return [
        state
        for state in list_competency_states(conn, user_id)
        if state.was_assessed and not state.is_solid
    ]


def set_goal(conn: sqlite3.Connection, user_id: int, module: ModuleView, now: datetime) -> None:
    with conn:
        conn.execute(
            "INSERT INTO user_goals (user_id, module_id, set_at) VALUES (?, ?, ?) "
            "ON CONFLICT (user_id) DO UPDATE SET module_id = excluded.module_id, "
            "set_at = excluded.set_at",
            (user_id, module.id, to_iso_utc(now)),
        )


def clear_goal(conn: sqlite3.Connection, user_id: int) -> None:
    with conn:
        conn.execute("DELETE FROM user_goals WHERE user_id = ?", (user_id,))


def find_goal(conn: sqlite3.Connection, user_id: int) -> ModuleView | None:
    row = conn.execute("SELECT module_id FROM user_goals WHERE user_id = ?", (user_id,)).fetchone()
    if row is None:
        return None
    return next(
        (module for module in list_module_views(conn, user_id) if module.id == row["module_id"]),
        None,
    )


def find_goal_path(conn: sqlite3.Connection, user_id: int) -> LearningPath | None:
    goal = find_goal(conn, user_id)
    return build_learning_path(conn, user_id, goal) if goal is not None else None


def get_goal_path(conn: sqlite3.Connection, user_id: int) -> LearningPath:
    path = find_goal_path(conn, user_id)
    if path is None:
        raise NoGoalError()
    return path
