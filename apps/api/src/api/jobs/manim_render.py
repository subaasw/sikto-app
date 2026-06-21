"""Render the Manim scenes in a lesson to video clips.

For each ``kind == manim`` scene with code, statically vet it, execute it via
``ManimRunner`` → an mp4, store the clip, and collect a {scene_id: data-URL} map
for the renderer plus a manifest for the player. Best-effort: a scene whose code
is unsafe, invalid, or whose render fails is simply skipped — it falls back to
the on-screen narration stub, and the lesson is never blocked.
"""

import base64
import json
import logging
import uuid
from typing import Protocol

from api.sandbox.manim import ManimRunner
from api.sandbox.manim_safety import is_safe_manim
from api.sandbox.types import RenderResult
from api.scenes.schema import SceneDocument, SceneKind
from api.storage import Storage
from api.storage_keys import MANIM_DATA_URL_PREFIX, manim_manifest_key, scene_manim_key

logger = logging.getLogger("api.manim")


class _Runner(Protocol):
    async def run(self, code: str, entry: str = "MainScene") -> RenderResult: ...


async def render_manim_clips(
    storage: Storage,
    job_id: uuid.UUID,
    document: SceneDocument,
    *,
    runner: _Runner | None = None,
) -> dict[str, str]:
    """Render every manim scene; return {scene_id: mp4 data-URL} for the renderer.
    Also persists each clip + a manifest so the web player can fetch them."""
    runner = runner or ManimRunner()
    clips: dict[str, str] = {}
    rendered: list[str] = []

    for scene in document.scenes:
        if scene.kind != SceneKind.manim or not scene.manim_code:
            continue
        if not is_safe_manim(scene.manim_code):
            logger.warning("job %s: manim scene %s failed the safety guard, skipping", job_id, scene.id)
            continue
        try:
            result = await runner.run(scene.manim_code, scene.manim_entry)
        except Exception:
            logger.warning("job %s: manim render failed for scene %s, skipping", job_id, scene.id, exc_info=True)
            continue
        if not result.video:
            continue
        storage.put(scene_manim_key(job_id, scene.id), result.video)
        clips[scene.id] = MANIM_DATA_URL_PREFIX + base64.b64encode(result.video).decode()
        rendered.append(scene.id)

    if rendered:
        storage.put(manim_manifest_key(job_id), json.dumps([{"scene_id": s} for s in rendered]).encode())
    return clips
