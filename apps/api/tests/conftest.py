"""Disposable PostgreSQL databases only; never reset the configured application DB."""

import asyncio
import os
import subprocess
import sys
from collections.abc import AsyncIterator, Iterator
from contextlib import contextmanager
from pathlib import Path
from uuid import uuid4

import asyncpg
import pytest
import pytest_asyncio
from fraggy_api.settings import Settings
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

ROOT = Path(__file__).resolve().parents[3]


def migrate(url: str, *arguments: str) -> str:
    environment = {**os.environ, "DATABASE_URL": url, "MIGRATION_DATABASE_URL": url}
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "alembic",
            "-c",
            str(ROOT / "apps/api/alembic.ini"),
            *arguments,
        ],
        cwd=ROOT,
        env=environment,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    return result.stdout + result.stderr


@contextmanager
def disposable_database() -> Iterator[str]:
    if os.getenv("RUN_DB_TESTS") != "1":
        pytest.skip("Set RUN_DB_TESTS=1 for disposable PostgreSQL integration tests")
    settings = Settings()
    parsed = make_url(settings.database_url.get_secret_value())
    if settings.app_env == "production" or parsed.host not in {
        "localhost",
        "127.0.0.1",
        "::1",
    }:
        pytest.fail(
            "Integration tests only create databases on non-production loopback PostgreSQL"
        )
    name = "fraggy_test_" + uuid4().hex
    admin_url = parsed.set(drivername="postgresql").render_as_string(
        hide_password=False
    )

    async def command(create: bool) -> None:
        connection = await asyncpg.connect(admin_url)
        try:
            if create:
                await connection.execute(f'CREATE DATABASE "{name}"')
            else:
                # Only this randomly named, test-owned database is terminated/dropped.
                await connection.execute(f'DROP DATABASE "{name}" WITH (FORCE)')
        finally:
            await connection.close()

    asyncio.run(command(True))
    try:
        yield parsed.set(database=name).render_as_string(hide_password=False)
    finally:
        asyncio.run(command(False))


@pytest.fixture(scope="session")
def catalog_url() -> Iterator[str]:
    with disposable_database() as url:
        migrate(url, "upgrade", "head")
        yield url


@pytest_asyncio.fixture
async def session(catalog_url: str) -> AsyncIterator[AsyncSession]:
    engine = create_async_engine(catalog_url, poolclass=NullPool)
    try:
        async with engine.connect() as connection:
            transaction = await connection.begin()
            try:
                async with AsyncSession(
                    bind=connection,
                    join_transaction_mode="create_savepoint",
                    expire_on_commit=False,
                ) as db:
                    yield db
            finally:
                await transaction.rollback()
    finally:
        await engine.dispose()
