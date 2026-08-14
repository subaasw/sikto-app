import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col

from api.enums import JobStatus
from api.models import Course, Job, Lesson, Notebook, ProductionRun, Source
from api.planning.schema import ProductionPlan
from api.scenes.schema import ElementType, SceneDocument


async def create_source_and_job(
    session: AsyncSession,
    source_type: str,
    raw_input: str,
    notebook_id: uuid.UUID | None = None,
    template: str = "explainer",
    mode: str = "auto",
    voice: str = "male",
    model: str | None = None,
    user_id: uuid.UUID | None = None,
) -> Job:
    source = Source(
        type=source_type,
        raw_input=raw_input,
        notebook_id=notebook_id,
        template=template,
        mode=mode,
        voice=voice,
        model=model,
    )
    session.add(source)
    await session.flush()
    job = Job(source_id=source.id, status=JobStatus.queued, user_id=user_id)
    session.add(job)
    await session.commit()
    await session.refresh(job)
    return job


async def get_job(session: AsyncSession, job_id: uuid.UUID) -> Job | None:
    return await session.get(Job, job_id)


async def list_recent_jobs(
    session: AsyncSession, user_id: uuid.UUID | None, limit: int = 20
) -> list[Job]:
    stmt = select(Job)
    if user_id is not None:
        stmt = stmt.where((col(Job.user_id) == user_id) | col(Job.user_id).is_(None))
    stmt = stmt.order_by(col(Job.created_at).desc()).limit(limit)
    return list((await session.execute(stmt)).scalars().all())


async def create_notebook(session: AsyncSession, title: str) -> Notebook:
    notebook = Notebook(title=title)
    session.add(notebook)
    await session.commit()
    await session.refresh(notebook)
    return notebook


async def get_notebook(session: AsyncSession, notebook_id: uuid.UUID) -> Notebook | None:
    return await session.get(Notebook, notebook_id)


async def list_notebook_source_ids(session: AsyncSession, notebook_id: uuid.UUID) -> list[str]:
    result = await session.execute(
        select(col(Source.id)).where(col(Source.notebook_id) == notebook_id)
    )
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


def _key_points_from_document(document: SceneDocument) -> list[str]:
    """Use each scene's heading as a key point (falls back to the title)."""
    points: list[str] = []
    for scene in document.scenes:
        for element in scene.elements:
            if element.type == ElementType.heading and element.text:
                points.append(element.text)
                break
    return points[:5] if points else [document.title]


async def create_lesson_from_scene_document(
    session: AsyncSession,
    job_id: uuid.UUID,
    source_id: uuid.UUID,
    document: SceneDocument,
    quiz: list[dict] | None = None,
) -> Lesson:
    lesson = Lesson(
        job_id=job_id,
        source_id=source_id,
        title=document.title,
        summary=document.summary,
        key_points=_key_points_from_document(document),
        quiz=quiz or [],
        script=document.model_dump(mode="json"),
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
    result = await session.execute(select(Lesson).where(col(Lesson.job_id) == job_id).limit(1))
    return result.scalar_one_or_none()


async def list_lessons(session: AsyncSession, limit: int = 50) -> list[Lesson]:
    """Most-recent lessons first, for the library/history view."""
    result = await session.execute(
        select(Lesson).order_by(col(Lesson.created_at).desc()).limit(limit)
    )
    return list(result.scalars().all())


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


# --- Courses (multi-module plans) ------------------------------------------


async def create_course(
    session: AsyncSession,
    job_id: uuid.UUID,
    source_id: uuid.UUID,
    *,
    title: str,
    summary: str,
    modules: list[dict],
) -> Course:
    course = Course(
        job_id=job_id, source_id=source_id, title=title, summary=summary, modules=modules
    )
    session.add(course)
    await session.commit()
    await session.refresh(course)
    return course


async def get_course(session: AsyncSession, course_id: uuid.UUID) -> Course | None:
    return await session.get(Course, course_id)


async def get_course_by_job(session: AsyncSession, job_id: uuid.UUID) -> Course | None:
    result = await session.execute(select(Course).where(col(Course.job_id) == job_id).limit(1))
    return result.scalar_one_or_none()


async def set_module_job(
    session: AsyncSession, course_id: uuid.UUID, order: int, module_job_id: uuid.UUID
) -> None:
    """Record which job is generating a module's lesson. Rewrites the whole
    modules JSON (list is tiny; a targeted JSONB update isn't worth it)."""
    course = await session.get(Course, course_id)
    if course is None:
        raise ValueError(f"course {course_id} not found")
    modules = [dict(m) for m in course.modules]
    for module in modules:
        if module.get("order") == order:
            module["job_id"] = str(module_job_id)
            break
    else:
        raise ValueError(f"course {course_id} has no module {order}")
    course.modules = modules
    await session.commit()
