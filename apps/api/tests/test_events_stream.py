import uuid

from httpx import ASGITransport, AsyncClient

from api.auth.repository import create_user
from api.db import SessionLocal
from api.jobs.repository import create_source_and_job, list_recent_jobs
from api.main import app
from api.models import Source


async def _client() -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def test_recent_jobs_include_unowned_legacy_rows():
    async with SessionLocal() as session:
        job = await create_source_and_job(session, source_type="text", raw_input="legacy")
        assert job.user_id is None
        jobs = await list_recent_jobs(session, user_id=uuid.uuid4())
        assert job.id in {j.id for j in jobs}


async def test_recent_jobs_exclude_other_users_jobs():
    async with SessionLocal() as session:
        owner = (
            await create_user(session, name="Owner", email="owner@example.com", password_hash="x")
        ).id
        other = (
            await create_user(session, name="Other", email="other@example.com", password_hash="x")
        ).id
        mine = await create_source_and_job(
            session, source_type="text", raw_input="mine", user_id=owner
        )
        theirs = await create_source_and_job(
            session, source_type="text", raw_input="theirs", user_id=other
        )
        visible = {j.id for j in await list_recent_jobs(session, user_id=owner)}
        assert mine.id in visible
        assert theirs.id not in visible


async def test_source_records_the_requested_model():
    async with await _client() as client:
        resp = await client.post(
            "/sources",
            json={"type": "text", "inputs": ["hello"], "model": "nope:not-a-real-model"},
        )
        assert resp.status_code == 201
    async with SessionLocal() as session:
        job = await list_recent_jobs(session, user_id=None, limit=1)
        source = await session.get(Source, job[0].source_id)
        assert source is not None
        assert source.model is None
