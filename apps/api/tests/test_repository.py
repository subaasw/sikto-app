from api.db import SessionLocal
from api.enums import JobStatus
from api.jobs.repository import create_source_and_job, get_job, update_job


async def test_create_and_fetch_job():
    async with SessionLocal() as session:
        job = await create_source_and_job(session, source_type="text", raw_input="hello")
        fetched = await get_job(session, job.id)
        assert fetched is not None
        assert fetched.status == JobStatus.queued
        assert fetched.source_id is not None


async def test_update_job_status():
    async with SessionLocal() as session:
        job = await create_source_and_job(session, source_type="text", raw_input="hi")
        await update_job(session, job.id, status=JobStatus.done, step="rendering")
        fetched = await get_job(session, job.id)
        assert fetched.status == JobStatus.done
        assert fetched.step == "rendering"
