from __future__ import annotations

from contextlib import closing

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from rich.text import Text

from hone import __version__
from hone.api.routes import router
from hone.api.schemas import ChallengeOut
from hone.api.theme import build_tokens_css
from hone.config import PROJECT_ROOT, load_settings
from hone.core.db import connect, latest_version, schema_version
from hone.core.users import UserNotFoundError
from hone.core.workspace import DatabaseMissingError, SchemaOutdatedError
from hone.engines.content import ContentFileMissingError
from hone.engines.progress import AmbiguousModuleError, UnknownModuleError
from hone.voice import challenge_for

DASHBOARD_DIR = PROJECT_ROOT / "dashboard"

CHALLENGE_STATUS_CODES: dict[type[Exception], int] = {
    DatabaseMissingError: 503,
    SchemaOutdatedError: 503,
    UserNotFoundError: 503,
    ContentFileMissingError: 500,
    UnknownModuleError: 404,
    AmbiguousModuleError: 409,
}

app = FastAPI(title="autonomia.dev", version=__version__)
app.include_router(router)
app.mount("/static", StaticFiles(directory=DASHBOARD_DIR), name="dashboard")


def _plain(markup: str) -> str:
    return Text.from_markup(markup).plain


async def _challenge_response(request: Request, error: Exception) -> JSONResponse:
    challenge = challenge_for(error)
    assert challenge is not None
    body = ChallengeOut(problem=_plain(challenge.problem), next_step=_plain(challenge.next_step))
    return JSONResponse(
        status_code=CHALLENGE_STATUS_CODES[type(error)], content={"challenge": body.model_dump()}
    )


for error_type in CHALLENGE_STATUS_CODES:
    app.add_exception_handler(error_type, _challenge_response)


@app.get("/", include_in_schema=False)
def dashboard_index() -> FileResponse:
    return FileResponse(DASHBOARD_DIR / "index.html")


@app.get("/theme/tokens.css", include_in_schema=False)
def theme_tokens() -> Response:
    return Response(build_tokens_css(), media_type="text/css")


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
