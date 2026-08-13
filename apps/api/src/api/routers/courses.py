"""Course endpoints: read a planned course and generate its modules on demand.

A `course`-mode source is planned into modules (see jobs/course_pipeline). Each
module is generated into its own normal video lesson lazily; modules unlock
sequentially (a module opens once the previous one's lesson is done)."""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from api.db import get_session
from api.jobs.repository import (
    create_source_and_job,
    get_course,
    get_course_by_job,
    get_job,
    get_source,
    set_module_job,
)

router = APIRouter(tags=["courses"])


class ModuleResponse(BaseModel):
    order: int
    title: str
    summary: str
    job_id: uuid.UUID | None
    status: str  # 'planned' | a job status ('queued'.. 'done' | 'failed')
    locked: bool  # sequential gate: previous module not done yet


class CourseResponse(BaseModel):
    id: uuid.UUID
    job_id: uuid.UUID
    title: str
    summary: str
    modules: list[ModuleResponse]


async def _module_status(session: AsyncSession, module: dict) -> str:
    job_id = module.get("job_id")
    if not job_id:
        return "planned"
    job = await get_job(session, uuid.UUID(str(job_id)))
    return job.status if job else "planned"


async def _course_response(session: AsyncSession, course) -> CourseResponse:
    modules = sorted((dict(m) for m in course.modules), key=lambda m: m.get("order", 0))
    out: list[ModuleResponse] = []
    prev_done = True
    for module in modules:
        status = await _module_status(session, module)
        out.append(
            ModuleResponse(
                order=module["order"],
                title=module["title"],
                summary=module["summary"],
                job_id=uuid.UUID(str(module["job_id"])) if module.get("job_id") else None,
                status=status,
                locked=not prev_done,
            )
        )
        prev_done = status == "done"
    return CourseResponse(
        id=course.id, job_id=course.job_id, title=course.title, summary=course.summary, modules=out
    )


@router.get("/courses/by-job/{job_id}", response_model=CourseResponse)
async def read_course_by_job(
    job_id: uuid.UUID, session: AsyncSession = Depends(get_session)
) -> CourseResponse:
    course = await get_course_by_job(session, job_id)
    if course is None:
        raise HTTPException(status_code=404, detail="course not found")
    return await _course_response(session, course)


class GenerateModuleResponse(BaseModel):
    job_id: uuid.UUID


@router.post(
    "/courses/{course_id}/modules/{order}/generate", response_model=GenerateModuleResponse
)
async def generate_module(
    course_id: uuid.UUID, order: int, session: AsyncSession = Depends(get_session)
) -> GenerateModuleResponse:
    course = await get_course(session, course_id)
    if course is None:
        raise HTTPException(status_code=404, detail="course not found")
    modules = sorted((dict(m) for m in course.modules), key=lambda m: m.get("order", 0))
    module = next((m for m in modules if m["order"] == order), None)
    if module is None:
        raise HTTPException(status_code=404, detail="module not found")

    # Idempotent: a module already has at most one generation job.
    if module.get("job_id"):
        return GenerateModuleResponse(job_id=uuid.UUID(str(module["job_id"])))

    # Sequential gate: the previous module's lesson must be done first.
    if order > 0:
        prev = next((m for m in modules if m["order"] == order - 1), None)
        prev_status = await _module_status(session, prev) if prev else "planned"
        if prev_status != "done":
            raise HTTPException(status_code=409, detail="previous module not finished")

    source = await get_source(session, course.source_id)
    if source is None or not source.text:
        raise HTTPException(status_code=409, detail="course source text unavailable")

    # Scope the lesson to this module: a focus preamble in front of the already
    # extracted course text (no re-fetching URLs). The brain naturally narrows.
    focus = (
        f'You are creating Module {order + 1} of {len(modules)} in a course titled '
        f'"{course.title}".\nThis module: {module["title"]} — {module["summary"]}\n'
        f"Teach ONLY this module's scope, in depth, drawing on the course material below. "
        f"Do not try to cover the whole course.\n\n---- COURSE MATERIAL ----\n\n{source.text}"
    )
    job = await create_source_and_job(
        session,
        source_type="text",
        raw_input=focus,
        template=source.template,
        mode="video",  # a normal lesson job, not another course plan
        voice=source.voice,
    )
    await set_module_job(session, course_id, order, job.id)
    return GenerateModuleResponse(job_id=job.id)
