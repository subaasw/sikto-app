from typing import Protocol

from api.agent.types import Passage
from api.engines.protocols import EmbeddingsClient, VectorStore
from api.knowledge.chunks import source_id_of


class Retriever(Protocol):
    async def retrieve(self, query: str, k: int) -> list[Passage]: ...


class EmbeddingRetriever:
    """Embeds a query and returns the nearest stored chunks as source-attributed
    passages. An optional ``source_ids`` scope limits retrieval to a set of sources
    (e.g. the sources in a notebook)."""

    def __init__(
        self,
        embeddings: EmbeddingsClient,
        vector_store: VectorStore,
        source_ids: list[str] | None = None,
    ) -> None:
        self._embeddings = embeddings
        self._vector_store = vector_store
        self._source_ids = source_ids

    async def retrieve(self, query: str, k: int) -> list[Passage]:
        [vector] = await self._embeddings.embed([query])
        hits = await self._vector_store.query(vector, k, self._source_ids)
        return [
            Passage(content=content, source_id=source_id_of(chunk_id), score=score)
            for chunk_id, content, score in hits
        ]
