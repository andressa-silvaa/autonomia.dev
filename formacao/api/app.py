from __future__ import annotations

from contextlib import closing

from fastapi import FastAPI

from formacao import __version__
from formacao.config import load_settings
from formacao.core.db import connect, latest_version, schema_version

app = FastAPI(title="Formação em TI", version=__version__)


@app.get("/health", description="API status and whether the database schema is up to date.")
def health() -> dict:
    settings = load_settings()
    latest = latest_version()
    if not settings.db_path.exists():
        return {"status": "no_database", "schema_version": 0, "latest_schema": latest}

    with closing(connect(settings.db_path)) as conn:
        version = schema_version(conn)
    status = "ok" if version == latest else "migrations_pending"
    return {"status": status, "schema_version": version, "latest_schema": latest}
