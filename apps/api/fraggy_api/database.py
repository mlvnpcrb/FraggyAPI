from collections.abc import AsyncIterator

from fastapi import Request
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from .settings import Settings


class Base(DeclarativeBase):
    """Shared metadata; models are registered explicitly, never created at startup."""


def create_engine(settings: Settings) -> AsyncEngine:
    return create_async_engine(
        settings.database_url.get_secret_value(),
        pool_pre_ping=True,
        pool_size=3,
        max_overflow=2,
        connect_args={
            "timeout": settings.database_timeout_seconds,
            "server_settings": {
                "statement_timeout": str(int(settings.database_timeout_seconds * 1000))
            },
            "statement_cache_size": 0,
            "prepared_statement_cache_size": 0,
        },
    )


async def get_session(request: Request) -> AsyncIterator[AsyncSession]:
    factory: async_sessionmaker[AsyncSession] = request.app.state.session_factory
    async with factory() as session:
        yield session
