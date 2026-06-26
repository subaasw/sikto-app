"""Vision QA: render a still of each scene and have a vision model flag visual
defects a schema check can't see — text overflow/clipping, overlapping elements,
crowding, poor contrast. Defects are emitted in the same ``scene <id>: ...``
format the validator uses, so they feed the existing repair loop.

Off by default: it needs a vision-capable model id (``vision_model``) and a render
service that exposes ``/render-still``, and it costs one render + one vision call
per scene. ``vision_reviewer_from_settings`` returns None unless it's configured,
so the brain simply skips the step.
"""

import base64
import json
import logging
import re
from typing import TYPE_CHECKING, Protocol

import httpx
from openai import AsyncOpenAI

from api.agent.providers import resolve_agent_llm
from api.config import Settings, get_settings
from api.scenes.schema import SceneDocument

if TYPE_CHECKING:
    from langchain_core.rate_limiters import BaseRateLimiter

logger = logging.getLogger("api.brain.vision")

VISION_SYSTEM = (
    "You are a layout QA reviewer for lesson video frames. Looking at the rendered frame, "
    "report ONLY real visual defects: text that overflows its area or is clipped, elements "
    "that overlap or collide, content that is crowded/cramped, or text with poor contrast "
    "against its background. Ignore matters of taste. If the frame looks clean, report nothing."
)

_ARRAY = re.compile(r"\[.*\]", re.DOTALL)


def _parse_problems(text: str) -> list[str]:
    """Pull a JSON array of short problem strings out of the model's reply."""
    match = _ARRAY.search(text or "")
    if not match:
        return []
    try:
        data = json.loads(match.group(0))
    except json.JSONDecodeError:
        return []
    return [str(p).strip() for p in data if isinstance(data, list) and str(p).strip()]


class VisionReviewer(Protocol):
    async def review(self, document: SceneDocument) -> list[str]: ...


class RenderVisionReviewer:
    """Renders a still per scene via the render service and inspects it with a
    vision model. Best-effort per scene — a failed still or inspection is skipped."""

    def __init__(
        self,
        *,
        render_url: str,
        client: AsyncOpenAI,
        model: str,
        timeout: float,
        rate_limiter: "BaseRateLimiter | None" = None,
    ) -> None:
        self._render_url = render_url.rstrip("/")
        self._client = client
        self._model = model
        self._timeout = timeout
        self._rate_limiter = rate_limiter

    async def review(self, document: SceneDocument) -> list[str]:
        issues: list[str] = []
        for scene in document.scenes:
            png = await self._still(document, scene.id)
            if png is None:
                continue
            for problem in await self._inspect(png):
                issues.append(f"scene {scene.id}: {problem}")
        return issues

    async def _still(self, document: SceneDocument, scene_id: str) -> bytes | None:
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.post(
                    f"{self._render_url}/render-still",
                    json={"document": document.model_dump(mode="json"), "scene_id": scene_id},
                )
                resp.raise_for_status()
                b64 = resp.json().get("image_b64")
                return base64.b64decode(b64) if b64 else None
        except Exception:
            logger.warning("still render failed for scene %s", scene_id, exc_info=True)
            return None

    async def _inspect(self, png: bytes) -> list[str]:
        data_uri = "data:image/png;base64," + base64.b64encode(png).decode()
        # Share the provider's throttle so vision calls count against the same
        # free-tier budget as the brain's text calls (NVIDIA: nvidia_rpm).
        if self._rate_limiter is not None:
            await self._rate_limiter.aacquire(blocking=True)
        try:
            resp = await self._client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": VISION_SYSTEM},
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": "List layout defects as a JSON array of short strings. "
                                "Return [] if the frame is clean.",
                            },
                            {"type": "image_url", "image_url": {"url": data_uri}},
                        ],
                    },
                ],
            )
            return _parse_problems(resp.choices[0].message.content or "[]")
        except Exception:
            logger.warning("vision inspection failed", exc_info=True)
            return []


def vision_reviewer_from_settings(settings: Settings | None = None) -> VisionReviewer | None:
    """A reviewer when Vision QA is enabled AND a vision model is configured; else
    None so the brain skips the step (the default)."""
    settings = settings or get_settings()
    if not settings.vision_qa_enabled or not settings.vision_model:
        return None
    try:
        cfg = resolve_agent_llm(settings)
    except Exception:
        logger.warning("vision QA enabled but no agent provider configured; skipping")
        return None
    client = AsyncOpenAI(
        base_url=cfg.base_url,
        api_key=cfg.api_key,
        timeout=settings.render_timeout_seconds,
        max_retries=0,
    )
    return RenderVisionReviewer(
        render_url=settings.render_url,
        client=client,
        model=settings.vision_model,
        timeout=settings.render_timeout_seconds,
        rate_limiter=cfg.rate_limiter,
    )
