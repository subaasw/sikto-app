from sqlalchemy import text


async def test_can_connect_and_select_one(db_conn):
    result = await db_conn.execute(text("SELECT 1"))
    assert result.scalar_one() == 1


async def test_pgvector_extension_available(db_conn):
    await db_conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
    result = await db_conn.execute(text("SELECT 1 FROM pg_extension WHERE extname = 'vector'"))
    assert result.scalar_one() == 1


async def test_core_tables_exist(db_conn):
    rows = await db_conn.execute(
        text(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_name IN ('sources','jobs')"
        )
    )
    names = {r[0] for r in rows}
    assert names == {"sources", "jobs"}
