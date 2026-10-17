import asyncio
import json
import logging
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from starlette.middleware.base import RequestResponseEndpoint
from starlette.responses import Response

from .database import create_engine, get_session
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
        app.state.session_factory = async_sessionmaker(engine, expire_on_commit=False)
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
                status_code=500, content={"detail": "Internal server error"}
            )
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
            status_code=500, content={"detail": "Internal server error"}
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
        return {"name": "FraggyAPI", "version": "0.1.0", "phase": "1B"}

    app.include_router(router)
    return app


app = create_app()
