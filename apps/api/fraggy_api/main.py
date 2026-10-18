import asyncio
import json
import logging
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, FastAPI, Request
from fastapi.exception_handlers import (
    http_exception_handler,
    request_validation_exception_handler,
)
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.exceptions import HTTPException
from starlette.middleware.base import RequestResponseEndpoint
from starlette.responses import Response

from .catalog_api import router as catalog_router
from .database import create_engine, get_session, request_session_factory
from .settings import Settings

logger = logging.getLogger("fraggy.api")


class JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        return json.dumps(
            {
                "timestamp": datetime.now(UTC).isoformat(),
                "level": record.levelname,
                "event": record.getMessage(),
            }
        )


handler = logging.StreamHandler()
handler.setFormatter(JSONFormatter())
logger.handlers = [handler]
logger.setLevel(logging.INFO)
logger.propagate = False


def create_app(settings: Settings | None = None) -> FastAPI:
    config = settings or Settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        engine = create_engine(config)
        app.state.session_factory = request_session_factory(engine)
        try:
            yield
        finally:
            await engine.dispose()

    app = FastAPI(
        title="FraggyAPI",
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/docs" if config.app_env == "development" else None,
        redoc_url=None,
        openapi_url="/openapi.json" if config.app_env == "development" else None,
    )
    app.state.settings = config
    app.include_router(catalog_router)

    @app.exception_handler(HTTPException)
    async def catalog_http_error(request: Request, exc: HTTPException) -> Response:
        if request.url.path.startswith("/api/v1/"):
            return JSONResponse(
                status_code=exc.status_code,
                content={
                    "error": {"code": str(exc.status_code), "message": str(exc.detail)}
                },
            )
        return await http_exception_handler(request, exc)

    @app.exception_handler(RequestValidationError)
    async def catalog_validation_error(
        request: Request, exc: RequestValidationError
    ) -> Response:
        if request.url.path.startswith("/api/v1/"):
            return JSONResponse(
                status_code=422,
                content={
                    "error": {
                        "code": "422",
                        "message": "Invalid request",
                        "details": [
                            {"location": list(error["loc"]), "type": error["type"]}
                            for error in exc.errors()
                        ],
                    }
                },
            )
        return await request_validation_exception_handler(request, exc)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.cors_origins,
        allow_methods=["GET"],
        allow_headers=["Content-Type"],
        allow_credentials=False,
    )

    @app.middleware("http")
    async def request_log(
        request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        started = time.monotonic()
        try:
            response = await call_next(request)
        except Exception as exc:
            logger.error("unhandled_exception type=%s", type(exc).__name__)
            response = JSONResponse(
                status_code=500,
                content=(
                    {"error": {"code": "500", "message": "Internal server error"}}
                    if request.url.path.startswith("/api/v1/")
                    else {"detail": "Internal server error"}
                ),
            )
        if request.url.path.startswith("/api/v1/"):
            response.headers["Cache-Control"] = "no-store"
        # Never log query strings, bodies, database URLs or exception messages.
        logger.info(
            "http_request method=%s status=%s duration_ms=%s",
            request.method,
            response.status_code,
            round((time.monotonic() - started) * 1000),
        )
        return response

    @app.exception_handler(Exception)
    async def unexpected_error(request: Request, exc: Exception) -> JSONResponse:
        logger.error("unhandled_exception type=%s", type(exc).__name__)
        return JSONResponse(
            status_code=500,
            content=(
                {"error": {"code": "500", "message": "Internal server error"}}
                if request.url.path.startswith("/api/v1/")
                else {"detail": "Internal server error"}
            ),
        )

    @app.get("/health", tags=["operations"])
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get(
        "/ready",
        tags=["operations"],
        responses={503: {"description": "Database unavailable"}},
    )
    async def ready(
        session: Annotated[AsyncSession, Depends(get_session)],
    ) -> JSONResponse:
        try:
            result = await asyncio.wait_for(
                session.execute(text("SELECT 1")),
                timeout=config.database_timeout_seconds,
            )
            if result.scalar_one() != 1:
                raise RuntimeError("Unexpected readiness result")
        except Exception as exc:
            logger.warning("database_unavailable type=%s", type(exc).__name__)
            return JSONResponse(status_code=503, content={"status": "not_ready"})
        return JSONResponse(content={"status": "ready"})

    router = APIRouter(prefix="/api/v1")

    @router.get("", tags=["metadata"])
    async def version() -> dict[str, str]:
        return {"name": "FraggyAPI", "version": "0.1.0", "phase": "2B"}

    app.include_router(router)
    return app


app = create_app()
