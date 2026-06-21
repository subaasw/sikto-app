"""End-to-end test of the brain-driven pipeline with fake collaborators.
Requires the database (uses real job/lesson rows)."""

from typing import Any

from api.db import SessionLocal
from api.engines.protocols import Document, TTSResult
from api.jobs.repository import create_source_and_job, get_job, get_lesson_by_job
from api.jobs.scene_pipeline import SceneEngines, run_scene_pipeline
from api.scenes.schema import Element, ElementType, Narration, Scene, SceneDocument


class FakeLoader:
    async def load(self, raw_input: str) -> Document:
        return Document(text="Cells are the unit of life.", title="Cells", type="text", meta={})


class FakeBrain:
    def __init__(self, document: SceneDocument) -> None:
        self._document = document
        self.calls: list[tuple[str, str]] = []

    async def generate(
        self, source_text: str, source_title: str, template=None, mode: str = "auto"
    ) -> SceneDocument:
        self.calls.append((source_text, source_title))
        return self._document


class FakeTTS:
    async def synthesize(
        self,
        text: str,
        *,
        rate: str | None = None,
        pitch: str | None = None,
        voice: str | None = None,
    ) -> TTSResult:
        return TTSResult(audio=b"AUDIO", duration_ms=2200)


class FakeSceneRenderer:
    def __init__(self) -> None:
        self.calls: list[tuple[SceneDocument, list[dict[str, Any]]]] = []

    async def render(
        self,
        document: SceneDocument,
        audio: list[dict[str, Any]],
        manim_clips: dict[str, str] | None = None,
    ) -> bytes:
        self.calls.append((document, audio))
        return b"MP4BYTES"


class MemStorage:
    def __init__(self) -> None:
        self.data: dict[str, bytes] = {}

    def put(self, key: str, data: bytes) -> str:
        self.data[key] = data
        return key

    def get(self, ref: str) -> bytes:
        return self.data[ref]

    def exists(self, ref: str) -> bool:
        return ref in self.data


def _document() -> SceneDocument:
    return SceneDocument(
        title="Cells",
        summary="The unit of life",
        scenes=[
            Scene(
                id="s0",
                narration=Narration(text="A cell is the smallest unit of life."),
                elements=[Element(id="s0-h", type=ElementType.heading, text="Cells")],
            )
        ],
    )


async def test_scene_pipeline_produces_lesson_and_video():
    document = _document()
    renderer = FakeSceneRenderer()
    storage = MemStorage()
    engines = SceneEngines(
        select_loader=lambda _raw: FakeLoader(),
        brain=FakeBrain(document),
        tts=FakeTTS(),
        scene_render=renderer,
        storage=storage,
    )

    async with SessionLocal() as session:
        job = await create_source_and_job(session, source_type="text", raw_input="some source")
        await run_scene_pipeline(session, job.id, engines)

        done = await get_job(session, job.id)
        assert done is not None and done.status == "done"

        lesson = await get_lesson_by_job(session, job.id)
        assert lesson is not None
        assert lesson.title == "Cells"
        assert lesson.video_url == f"renders/{job.id}/lesson.mp4"
        assert lesson.key_points == ["Cells"]
        assert lesson.script["scenes"][0]["id"] == "s0"

    # the renderer received a per-scene audio track as a data URL with its duration
    _, audio = renderer.calls[0]
    assert audio[0]["scene_id"] == "s0"
    assert audio[0]["url"].startswith("data:audio/mpeg;base64,")
    assert audio[0]["duration_ms"] == 2200
    assert b"MP4BYTES" in storage.data.values()
