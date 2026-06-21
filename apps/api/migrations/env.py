import asyncio

from alembic import context
from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel import SQLModel

import api.models  # noqa: F401  -- registers all tables on SQLModel.metadata
from api.config import get_settings

target_metadata = SQLModel.metadata


def run_migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async():
    engine = create_async_engine(get_settings().database_url)
    async with engine.connect() as connection:
        await connection.run_sync(run_migrations)
    await engine.dispose()


asyncio.run(run_async())
