from typing import Any

from api.engines.protocols import Document, TTSResult
from api.knowledge.chunks import source_id_of
from api.planning.schema import (
    Difficulty,
    Lesson,
    PlanMeta,
    ProductionPlan,
    QuizItem,
    Retrieval,
    RetrievalStrategy,
    Segment,
    VectorStoreName,
    VisualType,
    Voice,
)


class MockSourceLoader:
    async def load(self, raw_input: str) -> Document:
        return Document(text=f"loaded: {raw_input}", title="Mock", type="text", meta={})


class MockEmbeddingsClient:
    async def embed(self, texts: list[str]) -> list[list[float]]:
        return [[float(len(t) % 7)] * 8 for t in texts]


class MockVectorStore:
    def __init__(self) -> None:
        self._items: list[tuple[str, str, list[float]]] = []

    async def upsert(self, chunks: list[tuple[str, str, list[float]]]) -> None:
        self._items.extend(chunks)

    async def query(
        self, embedding: list[float], k: int, source_ids: list[str] | None = None
    ) -> list[tuple[str, str, float]]:
        items = self._items
        if source_ids is not None:
            allowed = set(source_ids)
            items = [item for item in items if source_id_of(item[0]) in allowed]
        return [(cid, content, 1.0) for cid, content, _ in items[:k]]


class MockTTSClient:
    async def synthesize(self, text: str) -> TTSResult:
        return TTSResult(audio=b"\x00" * 16, duration_ms=max(1, len(text)) * 50)


class MockRenderClient:
    async def render(self, plan: dict[str, Any]) -> str:
        return "renders/mock-lesson.mp4"


class MockPlanner:
    async def plan(self, document: Document, source_ids: list[str]) -> ProductionPlan:
        return ProductionPlan(
            lesson=Lesson(
                title="Mock Lesson",
                summary="A mock lesson.",
                difficulty=Difficulty.intro,
                key_points=["one", "two", "three"],
                quiz=[
                    QuizItem(question="Q1?", answer="A1", explanation="e1"),
                    QuizItem(question="Q2?", answer="A2", explanation="e2"),
                ],
            ),
            voice=Voice(id="default", language="en"),
            segments=[
                Segment(
                    id="s0",
                    order=0,
                    narration="Hello.",
                    caption="Hello",
                    visual_type=VisualType.title,
                )
            ],
            retrieval=Retrieval(strategy=RetrievalStrategy.direct, store=VectorStoreName.pgvector),
            meta=PlanMeta(
                source_ids=source_ids,
                planner_model="mock",
                embedding_model="mock",
                tts_model="mock",
                engine_version="0.0.0",
            ),
        )
