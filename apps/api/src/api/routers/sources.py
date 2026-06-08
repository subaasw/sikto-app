import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from api.db import get_session
from api.jobs.repository import create_source_and_job, get_job

router = APIRouter(tags=["sources"])


class CreateSourceRequest(BaseModel):
    type: str
    input: str


class CreateSourceResponse(BaseModel):
    job_id: uuid.UUID


class JobResponse(BaseModel):
    id: uuid.UUID
    status: str
    step: str | None
    error: str | None


@router.post("/sources", status_code=201, response_model=CreateSourceResponse)
async def create_source(
    body: CreateSourceRequest, session: AsyncSession = Depends(get_session)
) -> CreateSourceResponse:
    job = await create_source_and_job(session, source_type=body.type, raw_input=body.input)
    return CreateSourceResponse(job_id=job.id)


@router.get("/jobs/{job_id}", response_model=JobResponse)
async def read_job(job_id: uuid.UUID, session: AsyncSession = Depends(get_session)) -> JobResponse:
    job = await get_job(session, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="job not found")
    return JobResponse(id=job.id, status=job.status, step=job.step, error=job.error)
