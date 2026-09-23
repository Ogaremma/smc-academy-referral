from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import settings


def build_engine_kwargs(database_url: str) -> dict:
    """Return the engine options appropriate for the configured database.

    SQLite needs the thread-flag override. A server-managed PostgreSQL
    connection is closed by the server once it has been idle, so the pool must
    validate a connection before handing it to a request and recycle
    connections before they age out. Without this, the first request after an
    idle period (the Apps Script diagnostics call that opens a recovery run)
    is handed a dead connection and fails with an unhandled ``OperationalError``
    (HTTP 500), while the very next request succeeds.
    """
    if database_url.startswith("sqlite"):
        return {"connect_args": {"check_same_thread": False}}
    return {"pool_pre_ping": True, "pool_recycle": 1800}


engine = create_async_engine(
    settings.DATABASE_URL, echo=False, **build_engine_kwargs(settings.DATABASE_URL)
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for providing asynchronous database sessions."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
