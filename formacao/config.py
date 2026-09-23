from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent


@dataclass(frozen=True, slots=True)
class Settings:
    db_path: Path
    user_name: str
    api_host: str
    api_port: int


def _resolve_from_project_root(path: Path) -> Path:
    return path if path.is_absolute() else PROJECT_ROOT / path


def _parse_port(port_text: str) -> int:
    try:
        return int(port_text)
    except ValueError as exc:
        raise ValueError(f"FORMACAO_API_PORT must be a number, got {port_text!r}") from exc


def load_settings() -> Settings:
    load_dotenv(PROJECT_ROOT / ".env", override=False)
    return Settings(
        db_path=_resolve_from_project_root(Path(os.getenv("FORMACAO_DB_PATH", "data/formacao.db"))),
        user_name=os.getenv("FORMACAO_USER_NAME", "Estudante"),
        api_host=os.getenv("FORMACAO_API_HOST", "127.0.0.1"),
        api_port=_parse_port(os.getenv("FORMACAO_API_PORT", "8000")),
    )
