import base64
import json

import httpx

from api.engines.clients import HttpRenderClient, HttpTTSClient, RemotionCodeClient


async def test_tts_client_decodes_audio_and_duration():
    audio = b"abc123"

    def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        assert payload["text"] == "hello"
        return httpx.Response(
            200, json={"audio_b64": base64.b64encode(audio).decode(), "duration_ms": 250}
        )

    http = httpx.AsyncClient(transport=httpx.MockTransport(handler), base_url="http://tts")
    client = HttpTTSClient("http://tts", client=http)
    try:
        result = await client.synthesize("hello")
    finally:
        await http.aclose()

    assert result.audio == audio
    assert result.duration_ms == 250


async def test_render_client_returns_video_ref():
    def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        assert "plan" in payload
        return httpx.Response(200, json={"video_ref": "renders/x.mp4"})

    http = httpx.AsyncClient(transport=httpx.MockTransport(handler), base_url="http://render")
    client = HttpRenderClient("http://render", client=http)
    try:
        ref = await client.render({"plan": {}, "audio": []})
    finally:
        await http.aclose()

    assert ref == "renders/x.mp4"


async def test_remotion_code_client_decodes_video():
    clip = b"CLIPBYTES"

    def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        assert payload["code"] == "export const MainComposition = () => null;"
        assert payload["composition"] == "MainComposition"
        return httpx.Response(200, json={"video_b64": base64.b64encode(clip).decode()})

    http = httpx.AsyncClient(transport=httpx.MockTransport(handler), base_url="http://render")
    client = RemotionCodeClient("http://render", client=http)
    try:
        video = await client.render("export const MainComposition = () => null;", "MainComposition")
    finally:
        await http.aclose()

    assert video == clip
