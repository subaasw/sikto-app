import os

# Tests must NEVER touch the app's real database — the isolation fixture below
# truncates every table. Point the whole suite at a dedicated test database
# before anything imports the app's settings or engine. Override with
# TEST_POSTGRES_DB if you want a different name.
os.environ["POSTGRES_DB"] = os.getenv("TEST_POSTGRES_DB", "sikto_test")
os.environ.pop("DATABASE_URL", None)  # force recomposition from POSTGRES_* parts
# Production config bakes in no credentials, so the suite supplies its own
# (a real env / CI can still override any of these).
os.environ.setdefault("POSTGRES_USER", os.getenv("TEST_POSTGRES_USER", "sikto"))
os.environ.setdefault("POSTGRES_PASSWORD", os.getenv("TEST_POSTGRES_PASSWORD", "sikto"))
os.environ.setdefault("JWT_SECRET", "test-secret-not-for-production")

import pytest
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from api.db import engine

_TABLES = "users, notebooks, sources, jobs, source_chunks, lessons, production_runs"


@pytest.fixture(autouse=True)
async def _isolate_db():
    """Give each test a clean database and keep the module-level engine's pool
    from leaking asyncpg connections across pytest's per-test event loops.

    Truncation is best-effort: when no database is available the DB-free unit
    tests still run (the failure is swallowed and surfaces later for tests that
    actually need the database).
    """
    try:
        async with engine.begin() as conn:
            await conn.execute(text(f"TRUNCATE {_TABLES} RESTART IDENTITY CASCADE"))
    except (SQLAlchemyError, OSError):
        pass  # no database available → DB-free unit tests still run
    yield
    await engine.dispose()


@pytest.fixture
async def db_conn():
    async with engine.connect() as conn:
        yield conn
