from collections.abc import Callable

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.db import SessionLocal
from api.models import SourceChunk


class PgVectorStore:
    """VectorStore backed by Postgres + pgvector. Stores (id, content, embedding)
    rows in ``source_chunks`` and queries by cosine similarity."""

    def __init__(self, session_factory: Callable[[], AsyncSession] = SessionLocal) -> None:
        self._session_factory = session_factory

    async def upsert(self, chunks: list[tuple[str, str, list[float]]]) -> None:
        async with self._session_factory() as session:
            for chunk_id, content, embedding in chunks:
                existing = await session.get(SourceChunk, chunk_id)
                if existing is None:
                    session.add(SourceChunk(id=chunk_id, content=content, embedding=embedding))
                else:
                    existing.content = content
                    existing.embedding = embedding
            await session.commit()

    async def query(
        self, embedding: list[float], k: int, source_ids: list[str] | None = None
    ) -> list[tuple[str, str, float]]:
        async with self._session_factory() as session:
            distance = SourceChunk.embedding.cosine_distance(embedding)
            stmt = select(SourceChunk.id, SourceChunk.content, distance.label("distance"))
            if source_ids:
                # chunk ids are "<source_id>:<index>"; scope to the given sources.
                stmt = stmt.where(func.split_part(SourceChunk.id, ":", 1).in_(source_ids))
            stmt = stmt.order_by(distance).limit(k)
            result = await session.execute(stmt)
            return [(row.id, row.content, 1.0 - row.distance) for row in result]
