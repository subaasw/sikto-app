import base64
from typing import Any

import httpx

from api.config import get_settings
from api.engines.protocols import TTSResult, WordTiming
from api.scenes.schema import SceneDocument


class HttpTTSClient:
    """Calls the apps/tts service to synthesize narration audio."""

    def __init__(
        self,
        base_url: str,
        client: httpx.AsyncClient | None = None,
        timeout: float = 60.0,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._client = client
        self._timeout = timeout

    async def synthesize(
        self,
        text: str,
        *,
        rate: str | None = None,
        pitch: str | None = None,
        voice: str | None = None,
    ) -> TTSResult:
        url = f"{self._base_url}/synthesize"
        payload: dict[str, Any] = {"text": text}
        if rate is not None:
            payload["rate"] = rate
        if pitch is not None:
            payload["pitch"] = pitch
        if voice is not None:
            payload["voice"] = voice
        if self._client is not None:
            response = await self._client.post(url, json=payload)
        else:
            # Neural TTS for a few sentences can take longer than httpx's 5s
            # default; give it room so narration doesn't time out.
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.post(url, json=payload)
        response.raise_for_status()
        data = response.json()
        audio = base64.b64decode(data.get("audio_b64") or "")
        words = [
            WordTiming(text=w["text"], start_ms=int(w["start_ms"]), end_ms=int(w["end_ms"]))
            for w in data.get("words") or []
        ]
        return TTSResult(audio=audio, duration_ms=int(data["duration_ms"]), words=words)


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


class SceneRenderClient:
    """Renders a declarative SceneDocument to mp4 via the apps/render `/render-scene`
    endpoint, returning the video bytes."""

    def __init__(
        self,
        base_url: str,
        client: httpx.AsyncClient | None = None,
        timeout: float = 300.0,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._client = client
        self._timeout = timeout

    async def render(
        self,
        document: SceneDocument,
        audio: list[dict[str, Any]],
        manim_clips: dict[str, str] | None = None,
    ) -> bytes:
        url = f"{self._base_url}/render-scene"
        payload = {
            "document": document.model_dump(mode="json"),
            "audio": audio,
            "manim_clips": manim_clips or {},
        }
        if self._client is not None:
            response = await self._client.post(url, json=payload)
        else:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.post(url, json=payload)
        response.raise_for_status()
        return base64.b64decode(response.json()["video_b64"])


def tts_client_from_settings() -> HttpTTSClient:
    settings = get_settings()
    return HttpTTSClient(settings.tts_url, timeout=settings.tts_timeout_seconds)


def scene_render_client_from_settings() -> SceneRenderClient:
    settings = get_settings()
    return SceneRenderClient(settings.render_url, timeout=settings.render_timeout_seconds)


def render_client_from_settings() -> HttpRenderClient:
    return HttpRenderClient(get_settings().render_url)


def remotion_code_client_from_settings() -> RemotionCodeClient:
    return RemotionCodeClient(get_settings().render_url)
