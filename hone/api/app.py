from __future__ import annotations

from contextlib import closing

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from starlette.middleware.trustedhost import TrustedHostMiddleware

from hone import __version__
from hone.api import exercise_routes, knowledge_routes, routes, study_routes
from hone.api.schemas import ChallengeOut
from hone.api.theme import build_tokens_css
from hone.config import PROJECT_ROOT, load_settings
from hone.core.db import connect, latest_version, schema_version
from hone.core.users import UserNotFoundError
from hone.core.workspace import DatabaseMissingError, SchemaOutdatedError
from hone.engines.checkins import AlreadyCheckedInError, EmptyIntentionError
from hone.engines.content import ContentFileMissingError
from hone.engines.diagnostic import (
    DiagnosticIncompleteError,
    NoFinishedDiagnosticError,
    NoOpenDiagnosticError,
    NoQuestionsError,
    QuestionNotPendingError,
)
from hone.engines.exercises import (
    EmptyAnswerError,
    ExerciseNotStartedError,
    NoHintsLeftError,
    UnknownExerciseError,
)
from hone.engines.knowledge import NoGoalError
from hone.engines.progress import (
    AmbiguousModuleError,
    ModuleLockedError,
    RequiredExercisesPendingError,
    UnknownModuleError,
)
from hone.engines.sessions import ActiveSessionExistsError, NoActiveSessionError
from hone.engines.submissions import SelfAssessmentSizeError, WrongAnswerFormatError
from hone.voice import challenge_for

DASHBOARD_DIR = PROJECT_ROOT / "dashboard"
ALLOWED_HOSTS = ["127.0.0.1", "localhost"]
CLIENT_HEADER = "x-hone-client"
CLIENT_HEADER_VALUE = "dashboard"
SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}

CHALLENGE_STATUS_CODES: dict[type[Exception], int] = {
    DatabaseMissingError: 503,
    SchemaOutdatedError: 503,
    UserNotFoundError: 503,
    ContentFileMissingError: 500,
    UnknownModuleError: 404,
    UnknownExerciseError: 404,
    NoFinishedDiagnosticError: 404,
    NoGoalError: 404,
    AmbiguousModuleError: 409,
    ModuleLockedError: 409,
    RequiredExercisesPendingError: 409,
    ActiveSessionExistsError: 409,
    NoActiveSessionError: 409,
    AlreadyCheckedInError: 409,
    NoQuestionsError: 409,
    NoOpenDiagnosticError: 409,
    DiagnosticIncompleteError: 409,
    QuestionNotPendingError: 409,
    ExerciseNotStartedError: 409,
    NoHintsLeftError: 409,
    EmptyIntentionError: 422,
    EmptyAnswerError: 422,
    WrongAnswerFormatError: 422,
    SelfAssessmentSizeError: 422,
}

app = FastAPI(title="autonomia.dev", version=__version__)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=ALLOWED_HOSTS)
for router_module in (routes, study_routes, knowledge_routes, exercise_routes):
    app.include_router(router_module.router)
app.mount("/static", StaticFiles(directory=DASHBOARD_DIR), name="dashboard")


@app.middleware("http")
async def require_dashboard_header(request: Request, call_next):
    is_api_write = request.url.path.startswith("/api/") and request.method not in SAFE_METHODS
    if is_api_write and request.headers.get(CLIENT_HEADER) != CLIENT_HEADER_VALUE:
        return JSONResponse(status_code=403, content={"detail": "Missing dashboard header"})
    return await call_next(request)


async def _challenge_response(request: Request, error: Exception) -> JSONResponse:
    challenge = challenge_for(error)
    assert challenge is not None
    body = ChallengeOut(problem=challenge.problem, next_step=challenge.next_step)
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
