import httpx
from httpx import ASGITransport

from tts.main import app


async def test_health():
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"


async def test_synthesize_stub_returns_audio_meta():
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/synthesize", json={"text": "hi", "voice": "default"})
        assert resp.status_code == 200
        assert resp.json()["duration_ms"] > 0
