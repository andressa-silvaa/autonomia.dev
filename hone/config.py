from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OLLAMA_URL = "http://127.0.0.1:11434"
DEFAULT_OLLAMA_MODEL = "qwen2.5-coder:7b"
DEFAULT_EXERCISE_TIMEOUT_SECONDS = 10


@dataclass(frozen=True, slots=True)
class Settings:
    db_path: Path
    content_dir: Path
    exercises_dir: Path
    workspace_dir: Path
    user_name: str
    api_host: str
    api_port: int
    ollama_url: str
    ollama_model: str
    exercise_timeout_seconds: int


def _resolve_from_project_root(path: Path) -> Path:
    return path if path.is_absolute() else PROJECT_ROOT / path


def _parse_int(variable: str, default: int) -> int:
    text = os.getenv(variable, str(default))
    try:
        return int(text)
    except ValueError as exc:
        raise ValueError(f"{variable} must be a number, got {text!r}") from exc


def _path_setting(variable: str, default: str) -> Path:
    return _resolve_from_project_root(Path(os.getenv(variable, default)))


def load_settings() -> Settings:
    load_dotenv(PROJECT_ROOT / ".env", override=False)
    return Settings(
        db_path=_path_setting("HONE_DB_PATH", "data/hone.db"),
        content_dir=_path_setting("HONE_CONTENT_DIR", "data"),
        exercises_dir=_path_setting("HONE_EXERCISES_DIR", "exercises"),
        workspace_dir=_path_setting("HONE_WORKSPACE_DIR", "workspace"),
        user_name=os.getenv("HONE_USER_NAME", "Estudante"),
        api_host=os.getenv("HONE_API_HOST", "127.0.0.1"),
        api_port=_parse_int("HONE_API_PORT", 8000),
        ollama_url=os.getenv("HONE_OLLAMA_URL", DEFAULT_OLLAMA_URL).rstrip("/"),
        ollama_model=os.getenv("HONE_OLLAMA_MODEL", DEFAULT_OLLAMA_MODEL),
        exercise_timeout_seconds=_parse_int(
            "HONE_EXERCISE_TIMEOUT", DEFAULT_EXERCISE_TIMEOUT_SECONDS
        ),
    )
