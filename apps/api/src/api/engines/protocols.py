from dataclasses import dataclass
from typing import Any, Protocol


@dataclass
class Document:
    text: str
    title: str | None
    type: str
    meta: dict[str, Any]


@dataclass
class TTSResult:
    audio: bytes
    duration_ms: int


class SourceLoader(Protocol):
    async def load(self, raw_input: str) -> Document: ...


class EmbeddingsClient(Protocol):
    async def embed(self, texts: list[str]) -> list[list[float]]: ...


class VectorStore(Protocol):
    async def upsert(self, chunks: list[tuple[str, str, list[float]]]) -> None: ...
    async def query(
        self, embedding: list[float], k: int, source_ids: list[str] | None = None
    ) -> list[tuple[str, str, float]]: ...


class TTSClient(Protocol):
    async def synthesize(self, text: str) -> TTSResult: ...


class RenderClient(Protocol):
    async def render(self, plan: dict[str, Any]) -> str: ...
