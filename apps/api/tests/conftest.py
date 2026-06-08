import pytest

from api.db import engine


@pytest.fixture
async def db_conn():
    async with engine.connect() as conn:
        yield conn
