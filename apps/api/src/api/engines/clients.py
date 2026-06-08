import base64
from typing import Any

import httpx

from api.config import get_settings
from api.engines.protocols import TTSResult


class HttpTTSClient:
    """Calls the apps/tts service to synthesize narration audio."""

    def __init__(self, base_url: str, client: httpx.AsyncClient | None = None) -> None:
        self._base_url = base_url.rstrip("/")
        self._client = client

    async def synthesize(self, text: str) -> TTSResult:
        url = f"{self._base_url}/synthesize"
        payload = {"text": text}
        if self._client is not None:
            response = await self._client.post(url, json=payload)
        else:
            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=payload)
        response.raise_for_status()
        data = response.json()
        audio = base64.b64decode(data.get("audio_b64") or "")
        return TTSResult(audio=audio, duration_ms=int(data["duration_ms"]))


class HttpRenderClient:
    """Calls the apps/render service to render and assemble the final video."""

    def __init__(self, base_url: str, client: httpx.AsyncClient | None = None) -> None:
        self._base_url = base_url.rstrip("/")
        self._client = client

    async def render(self, plan: dict[str, Any]) -> str:
        url = f"{self._base_url}/render"
        if self._client is not None:
            response = await self._client.post(url, json=plan)
        else:
            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=plan)
        response.raise_for_status()
        return str(response.json()["video_ref"])


class RemotionCodeClient:
    """Sends AI-generated Remotion code to the apps/render service and returns the
    rendered clip bytes. Matches the SegmentRenderer's remotion_render callable."""

    def __init__(self, base_url: str, client: httpx.AsyncClient | None = None) -> None:
        self._base_url = base_url.rstrip("/")
        self._client = client

    async def render(self, code: str, entry: str) -> bytes:
        url = f"{self._base_url}/render-code"
        payload = {"code": code, "composition": entry}
        if self._client is not None:
            response = await self._client.post(url, json=payload)
        else:
            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=payload)
        response.raise_for_status()
        return base64.b64decode(response.json()["video_b64"])


def tts_client_from_settings() -> HttpTTSClient:
    return HttpTTSClient(get_settings().tts_url)


def render_client_from_settings() -> HttpRenderClient:
    return HttpRenderClient(get_settings().render_url)


def remotion_code_client_from_settings() -> RemotionCodeClient:
    return RemotionCodeClient(get_settings().render_url)
