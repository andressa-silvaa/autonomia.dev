from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Any


class TableReader:
    def __init__(self, table: dict[str, Any], location: str, problems: list[str]) -> None:
        self._table = table
        self._location = location
        self._problems = problems

    def has(self, key: str) -> bool:
        return key in self._table

    def text(self, key: str, *, required: bool = True) -> str:
        value = self._table.get(key, None if required else "")
        if not isinstance(value, str) or (required and not value.strip()):
            self._problems.append(f"{self._location}: field '{key}' must be a non-empty string")
            return ""
        return value.strip()

    def text_list(self, key: str) -> tuple[str, ...]:
        value = self._table.get(key, [])
        if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
            self._problems.append(f"{self._location}: field '{key}' must be a list of strings")
            return ()
        return tuple(value)

    def boolean(self, key: str, *, default: bool) -> bool:
        value = self._table.get(key, default)
        if not isinstance(value, bool):
            self._problems.append(f"{self._location}: field '{key}' must be true or false")
            return default
        return value

    def integer(self, key: str) -> int | None:
        value = self._table.get(key)
        if not isinstance(value, int) or isinstance(value, bool):
            self._problems.append(f"{self._location}: field '{key}' must be an integer")
            return None
        return value


def read_toml(path: Path, problems: list[str]) -> dict[str, Any]:
    try:
        with path.open("rb") as file:
            return tomllib.load(file)
    except FileNotFoundError:
        problems.append(f"{path}: file not found")
    except tomllib.TOMLDecodeError as exc:
        problems.append(f"{path}: invalid TOML ({exc})")
    return {}


def read_tables(document: dict[str, Any], key: str, path: Path, problems: list[str]) -> list[dict]:
    value = document.get(key, [])
    if not isinstance(value, list) or not all(isinstance(item, dict) for item in value):
        problems.append(f"{path}: '{key}' must be an array of tables ([[{key}]])")
        return []
    return value
