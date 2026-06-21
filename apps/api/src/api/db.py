from collections.abc import AsyncIterator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlmodel.ext.asyncio.session import AsyncSession

from api.config import get_settings

_settings = get_settings()
engine = create_async_engine(_settings.database_url, future=True)
SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_session() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as session:
        yield session


async def check_connection() -> None:
    """Open a connection and run a trivial query. Raises on failure."""
    async with engine.connect() as conn:
        await conn.execute(text("SELECT 1"))
