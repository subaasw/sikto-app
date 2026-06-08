import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.enums import JobStatus
from api.models import Job, Lesson, Notebook, ProductionRun, Source
from api.planning.schema import ProductionPlan


async def create_source_and_job(
    session: AsyncSession,
    source_type: str,
    raw_input: str,
    notebook_id: uuid.UUID | None = None,
) -> Job:
    source = Source(type=source_type, raw_input=raw_input, notebook_id=notebook_id)
    session.add(source)
    await session.flush()
    job = Job(source_id=source.id, status=JobStatus.queued)
    session.add(job)
    await session.commit()
    await session.refresh(job)
    return job


async def get_job(session: AsyncSession, job_id: uuid.UUID) -> Job | None:
    return await session.get(Job, job_id)


async def create_notebook(session: AsyncSession, title: str) -> Notebook:
    notebook = Notebook(title=title)
    session.add(notebook)
    await session.commit()
    await session.refresh(notebook)
    return notebook


async def get_notebook(session: AsyncSession, notebook_id: uuid.UUID) -> Notebook | None:
    return await session.get(Notebook, notebook_id)


async def list_notebook_source_ids(session: AsyncSession, notebook_id: uuid.UUID) -> list[str]:
    result = await session.execute(select(Source.id).where(Source.notebook_id == notebook_id))
    return [str(row[0]) for row in result]


async def update_job(
    session: AsyncSession,
    job_id: uuid.UUID,
    *,
    status: JobStatus | None = None,
    step: str | None = None,
    error: str | None = None,
) -> None:
    job = await session.get(Job, job_id)
    if job is None:
        raise ValueError(f"job {job_id} not found")
    if status is not None:
        job.status = status
    if step is not None:
        job.step = step
    if error is not None:
        job.error = error
    await session.commit()


async def get_source(session: AsyncSession, source_id: uuid.UUID) -> Source | None:
    return await session.get(Source, source_id)


async def update_source_content(
    session: AsyncSession, source_id: uuid.UUID, *, text: str, title: str | None
) -> None:
    source = await session.get(Source, source_id)
    if source is None:
        raise ValueError(f"source {source_id} not found")
    source.text = text
    source.title = title
    await session.commit()


async def create_lesson(
    session: AsyncSession, job_id: uuid.UUID, source_id: uuid.UUID, plan: ProductionPlan
) -> Lesson:
    lesson = Lesson(
        job_id=job_id,
        source_id=source_id,
        title=plan.lesson.title,
        summary=plan.lesson.summary,
        key_points=list(plan.lesson.key_points),
        quiz=[item.model_dump() for item in plan.lesson.quiz],
        script={"segments": [segment.model_dump(mode="json") for segment in plan.segments]},
        video_url=None,
    )
    session.add(lesson)
    await session.commit()
    await session.refresh(lesson)
    return lesson


async def set_lesson_video(session: AsyncSession, lesson_id: uuid.UUID, video_url: str) -> None:
    lesson = await session.get(Lesson, lesson_id)
    if lesson is None:
        raise ValueError(f"lesson {lesson_id} not found")
    lesson.video_url = video_url
    await session.commit()


async def get_lesson_by_job(session: AsyncSession, job_id: uuid.UUID) -> Lesson | None:
    result = await session.execute(select(Lesson).where(Lesson.job_id == job_id).limit(1))
    return result.scalar_one_or_none()


async def save_production_run(
    session: AsyncSession, job_id: uuid.UUID, plan: ProductionPlan
) -> None:
    run = ProductionRun(
        job_id=job_id,
        plan=plan.model_dump(mode="json"),
        planner_model=plan.meta.planner_model,
        embedding_model=plan.meta.embedding_model,
        tts_model=plan.meta.tts_model,
        engine_version=plan.meta.engine_version,
    )
    session.add(run)
    await session.commit()
