import uuid
from collections.abc import Callable
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from api.engines.protocols import (
    EmbeddingsClient,
    SourceLoader,
    TTSClient,
    VectorStore,
)
from api.enums import JobStatus
from api.ingestion.chunking import chunk_text
from api.jobs.repository import (
    create_lesson,
    get_job,
    get_source,
    save_production_run,
    set_lesson_video,
    update_job,
    update_source_content,
)
from api.knowledge.chunks import chunk_id
from api.planning.engine import Planner
from api.storage import Storage
from api.visuals.assembler import Assembler
from api.visuals.renderer import SegmentRenderer


@dataclass
class Engines:
    select_loader: Callable[[str], SourceLoader]
    embeddings: EmbeddingsClient
    vectors: VectorStore
    planner: Planner
    tts: TTSClient
    segment_renderer: SegmentRenderer
    assembler: Assembler
    storage: Storage


async def run_pipeline(session: AsyncSession, job_id: uuid.UUID, engines: Engines) -> None:
    job = await get_job(session, job_id)
    if job is None:
        raise ValueError(f"job {job_id} not found")
    source = await get_source(session, job.source_id)
    if source is None:
        raise ValueError(f"source {job.source_id} not found")
    source_id = source.id
    raw_input = source.raw_input

    try:
        await update_job(session, job_id, status=JobStatus.loading, step="loading")
        loader = engines.select_loader(raw_input)
        document = await loader.load(raw_input)
        await update_source_content(session, source_id, text=document.text, title=document.title)

        await update_job(session, job_id, status=JobStatus.embedding, step="embedding")
        chunks = chunk_text(document.text)
        if chunks:
            vectors = await engines.embeddings.embed(chunks)
            records = [
                (chunk_id(str(source_id), index), chunk, vector)
                for index, (chunk, vector) in enumerate(zip(chunks, vectors, strict=True))
            ]
            await engines.vectors.upsert(records)

        await update_job(session, job_id, status=JobStatus.planning, step="planning")
        plan = await engines.planner.plan(document, [str(source_id)])
        await save_production_run(session, job_id, plan)
        lesson = await create_lesson(session, job_id, source_id, plan)

        await update_job(session, job_id, status=JobStatus.narrating, step="narrating")
        audios: list[bytes] = []
        for segment in plan.segments:
            result = await engines.tts.synthesize(segment.narration)
            engines.storage.put(f"audio/{job_id}/{segment.id}.m4a", result.audio)
            audios.append(result.audio)

        await update_job(session, job_id, status=JobStatus.rendering, step="rendering")
        clips: list[tuple[bytes, bytes]] = []
        for segment, audio in zip(plan.segments, audios, strict=True):
            video = await engines.segment_renderer.render_segment(segment)
            clips.append((video, audio))
        final_video = await engines.assembler.assemble(clips)
        video_ref = engines.storage.put(f"renders/{job_id}/lesson.mp4", final_video)
        await set_lesson_video(session, lesson.id, video_ref)

        await update_job(session, job_id, status=JobStatus.done, step="done")
    except Exception as exc:
        current = await get_job(session, job_id)
        step = current.step if current else None
        await update_job(session, job_id, status=JobStatus.failed, step=step, error=str(exc))
