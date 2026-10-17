import asyncio
import os
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient
from fraggy_api.database import get_session
from fraggy_api.main import create_app
from fraggy_api.settings import Settings
from pydantic import SecretStr, ValidationError


def test_health_version_and_docs() -> None:
    with TestClient(create_app()) as client:
        assert client.get("/health").json() == {"status": "ok"}
        assert client.get("/api/v1").json()["phase"] == "1B"
        assert client.get("/docs").status_code == 200


def test_docs_disabled_outside_development() -> None:
    with TestClient(create_app(Settings(app_env="production"))) as client:
        assert client.get("/docs").status_code == 404
        assert client.get("/openapi.json").status_code == 404


@pytest.mark.parametrize("available", [True, False])
def test_readiness_queries_database_and_sanitizes_failures(available: bool) -> None:
    app = create_app()
    session = AsyncMock()
    if available:
        result = MagicMock()
        result.scalar_one.return_value = 1
        session.execute.return_value = result
    else:
        session.execute.side_effect = RuntimeError("private connection details")
    app.dependency_overrides[get_session] = lambda: session
    with TestClient(app) as client:
        response = client.get("/ready")
    assert response.status_code == (200 if available else 503)
    assert response.json() == {"status": "ready" if available else "not_ready"}
    assert "private" not in response.text
    assert str(session.execute.call_args.args[0]) == "SELECT 1"


def test_safe_unexpected_error() -> None:
    app = create_app()

    @app.get("/test-error")
    async def broken() -> None:
        raise RuntimeError("private details")

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/test-error")
        assert response.status_code == 500
        assert response.json() == {"detail": "Internal server error"}


def test_cors_allowlist() -> None:
    with TestClient(create_app()) as client:
        response = client.get("/health", headers={"Origin": "http://localhost:3000"})
        assert (
            response.headers["access-control-allow-origin"] == "http://localhost:3000"
        )
        response = client.get(
            "/health", headers={"Origin": "https://untrusted.invalid"}
        )
        assert "access-control-allow-origin" not in response.headers


def test_rejects_wrong_database_driver_and_wildcard_cors() -> None:
    with pytest.raises(ValidationError):
        Settings(database_url=SecretStr("sqlite:///test.db"))
    with pytest.raises(ValidationError):
        Settings(cors_origins=["*"])


@pytest.mark.skipif(
    os.getenv("RUN_DB_TESTS") != "1", reason="Requires local PostgreSQL"
)
def test_real_database_readiness() -> None:
    with TestClient(create_app()) as client:
        assert client.get("/ready").status_code == 200


@pytest.mark.asyncio
async def test_readiness_timeout_returns_503() -> None:
    app = create_app(Settings(database_timeout_seconds=0.01))
    session = AsyncMock()

    async def slow_query(*args: object) -> None:
        await asyncio.sleep(1)

    session.execute.side_effect = slow_query
    app.dependency_overrides[get_session] = lambda: session
    with TestClient(app) as client:
        response = client.get("/ready")
    assert response.status_code == 503
    assert response.json() == {"status": "not_ready"}


def test_readiness_requires_expected_query_result() -> None:
    app = create_app()
    session = AsyncMock()
    result = MagicMock()
    result.scalar_one.return_value = 0
    session.execute.return_value = result
    app.dependency_overrides[get_session] = lambda: session
    with TestClient(app) as client:
        assert client.get("/ready").status_code == 503


@pytest.mark.parametrize(
    "origin",
    [
        "*",
        "https://user:pass@example.com",
        "https://example.com/path",
        "https://example.com?key=value",
    ],
)
def test_rejects_invalid_cors_origins(origin: str) -> None:
    with pytest.raises(ValidationError):
        Settings(cors_origins=[origin])
