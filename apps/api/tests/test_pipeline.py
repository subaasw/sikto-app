from collections.abc import Sequence

from api.db import SessionLocal
from api.engines.mocks import (
    MockEmbeddingsClient,
    MockPlanner,
    MockSourceLoader,
    MockTTSClient,
    MockVectorStore,
)
from api.enums import JobStatus
from api.jobs.pipeline import Engines, run_pipeline
from api.jobs.repository import create_source_and_job, get_job, get_lesson_by_job
from api.planning.schema import Segment
from api.storage import LocalStorage


class FakeSegmentRenderer:
    async def render_segment(self, segment: Segment) -> bytes:
        return b"CLIP"


class FakeAssembler:
    def __init__(self) -> None:
        self.clips: Sequence[tuple[bytes, bytes]] = []

    async def assemble(self, clips: Sequence[tuple[bytes, bytes]]) -> bytes:
        self.clips = clips
        return b"FINAL"


def _engines(tmp_path, *, loader=None) -> Engines:
    chosen = loader or MockSourceLoader()
    return Engines(
        select_loader=lambda _raw: chosen,
        embeddings=MockEmbeddingsClient(),
        vectors=MockVectorStore(),
        planner=MockPlanner(),
        tts=MockTTSClient(),
        segment_renderer=FakeSegmentRenderer(),
        assembler=FakeAssembler(),
        storage=LocalStorage(str(tmp_path)),
    )


async def test_pipeline_runs_job_to_done_and_persists_lesson(tmp_path):
    async with SessionLocal() as session:
        job = await create_source_and_job(session, source_type="text", raw_input="hi")
        await run_pipeline(session, job.id, _engines(tmp_path))

        done = await get_job(session, job.id)
        assert done.status == JobStatus.done

        lesson = await get_lesson_by_job(session, job.id)
        assert lesson is not None
        assert lesson.title == "Mock Lesson"
        assert lesson.video_url.endswith("lesson.mp4")


async def test_pipeline_marks_failed_on_step_error(tmp_path):
    class BoomLoader:
        async def load(self, raw_input: str):
            raise RuntimeError("boom")

    async with SessionLocal() as session:
        job = await create_source_and_job(session, source_type="text", raw_input="hi")
        await run_pipeline(session, job.id, _engines(tmp_path, loader=BoomLoader()))

        failed = await get_job(session, job.id)
        assert failed.status == JobStatus.failed
        assert failed.step == "loading"
        assert "boom" in (failed.error or "")
