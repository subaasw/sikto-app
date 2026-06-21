"""DB-dependent: requires Postgres + pgvector with migration 0002 applied
(a local Postgres running, then `uv run alembic upgrade head`)."""

from api.knowledge.vector_store import PgVectorStore
from api.models import EMBEDDING_DIM


def _vec(*head: float) -> list[float]:
    values = list(head)
    return values + [0.0] * (EMBEDDING_DIM - len(values))


async def test_upsert_then_query_returns_nearest_first():
    store = PgVectorStore()
    await store.upsert(
        [
            ("k1", "apple", _vec(1.0, 0.0)),
            ("k2", "banana", _vec(0.0, 1.0)),
        ]
    )
    hits = await store.query(_vec(1.0, 0.0), k=1)
    assert hits[0][0] == "k1"
    assert hits[0][1] == "apple"


async def test_upsert_updates_existing_content():
    store = PgVectorStore()
    await store.upsert([("k1", "old", _vec(1.0, 0.0))])
    await store.upsert([("k1", "new", _vec(1.0, 0.0))])
    hits = await store.query(_vec(1.0, 0.0), k=1)
    assert hits[0][1] == "new"
