import httpx
from httpx import ASGITransport

from api.jobs.worker import process_next_job
from api.main import app


async def _client() -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def test_post_sources_creates_queued_job():
    async with await _client() as client:
        resp = await client.post("/sources", json={"type": "text", "input": "hello"})
        assert resp.status_code == 201
        job_id = resp.json()["job_id"]
        status = await client.get(f"/jobs/{job_id}")
        assert status.status_code == 200
        assert status.json()["status"] == "queued"


async def test_job_reaches_done_after_worker_runs():
    async with await _client() as client:
        resp = await client.post("/sources", json={"type": "text", "input": "hello"})
        job_id = resp.json()["job_id"]
        await process_next_job()
        status = await client.get(f"/jobs/{job_id}")
        assert status.json()["status"] == "done"
