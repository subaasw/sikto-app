"""Render the Manim scenes in a lesson to video clips.

For each ``kind == manim`` scene with code, statically vet it, execute it via
``ManimRunner`` → an mp4, store the clip, and collect a {scene_id: data-URL} map
for the renderer plus a manifest for the player. Best-effort: a scene whose code
is unsafe, invalid, or whose render fails is simply skipped — it falls back to
the on-screen narration stub, and the lesson is never blocked.
"""

import asyncio
import base64
import json
import logging
import os
import shutil
import subprocess
import tempfile
import uuid
from collections.abc import Awaitable, Callable
from typing import Protocol

from pydantic import BaseModel, Field

from api.agent_engine.llm import StructuredLLM
from api.sandbox.manim import ManimRunner
from api.sandbox.manim_safety import is_safe_manim
from api.sandbox.types import RenderResult
from api.scenes.schema import SceneDocument, SceneKind
from api.storage import Storage
from api.storage_keys import MANIM_DATA_URL_PREFIX, manim_manifest_key, scene_manim_key

logger = logging.getLogger("api.manim")

# Given broken code + the reason it failed, return fixed code (or None to give up).
Repair = Callable[[str, str], Awaitable[str | None]]
# Pad a silent clip's last frame so it lasts at least target_ms (best-effort, ffmpeg).
Pad = Callable[[bytes, int], Awaitable[bytes]]

_MAX_REPAIRS = 2  # render → repair → render → repair → render
_PAD_TOLERANCE_MS = 300  # don't bother padding sub-third-second gaps

_REPAIR_SYSTEM = (
    "You fix a broken Manim Community scene. You are given the failing manim_code and the "
    "error it produced. Return corrected, self-contained code: a Scene subclass named MainScene, "
    "valid Manim Python only (no prose, no imports beyond manim/numpy/math/random), no network or "
    "filesystem access. Change as little as needed to make it render."
)


class _ManimFix(BaseModel):
    manim_code: str = Field(description="The corrected self-contained Manim Scene named MainScene.")


def llm_manim_repair(llm: StructuredLLM) -> Repair:
    """A ``Repair`` that asks the brain's LLM to fix failing Manim code from the error."""

    async def repair(code: str, error: str) -> str | None:
        prompt = f"The error was:\n{error}\n\nThe failing manim_code:\n{code}"
        fix = await llm.generate(_REPAIR_SYSTEM, prompt, _ManimFix)
        return fix.manim_code or None

    return repair


class _Runner(Protocol):
    async def run(self, code: str, entry: str = "MainScene") -> RenderResult: ...


async def _vet_and_run(runner: _Runner, code: str, entry: str) -> tuple[RenderResult | None, str]:
    """Safety-check then render. Returns (result, "") on success or (None, reason)."""
    if not is_safe_manim(code):
        return None, "code failed the safety guard — use only manim, numpy, math, random"
    try:
        result = await runner.run(code, entry)
    except Exception as exc:  # render/compile error → the reason feeds the repair
        return None, f"manim render error: {exc}"
    if not result.video:
        return None, "manim produced no video output"
    return result, ""


async def _probe_ms(path: str) -> int:
    """Duration of a video in ms via ffprobe, or 0 if it can't be read."""
    proc = await asyncio.create_subprocess_exec(
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=nw=1:nk=1", path,
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
    )
    out, _ = await proc.communicate()
    try:
        return round(float(out.decode().strip()) * 1000)
    except (ValueError, AttributeError):
        return 0


async def _pad_to_ms(video: bytes, target_ms: int) -> bytes:
    """Freeze the last frame so the clip lasts at least ``target_ms`` (to cover the
    narration). Returns the input unchanged when it's already long enough or when
    ffprobe/ffmpeg is unavailable — padding is a polish step, never a hard error."""
    workdir = tempfile.mkdtemp(prefix="sikto-manim-pad-")
    try:
        src = os.path.join(workdir, "in.mp4")
        out = os.path.join(workdir, "out.mp4")
        with open(src, "wb") as handle:
            handle.write(video)
        current = await _probe_ms(src)
        if current <= 0 or target_ms - current <= _PAD_TOLERANCE_MS:
            return video
        delta_s = (target_ms - current) / 1000
        proc = await asyncio.create_subprocess_exec(
            "ffmpeg", "-y", "-i", src,
            "-vf", f"tpad=stop_mode=clone:stop_duration={delta_s:.3f}",
            "-an", out,
            stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
        )
        _, err = await proc.communicate()
        if proc.returncode != 0 or not os.path.exists(out):
            logger.warning("manim pad failed: %s", err.decode(errors="replace")[-300:])
            return video
        with open(out, "rb") as handle:
            return handle.read()
    except Exception:
        logger.warning("manim pad raised, keeping unpadded clip", exc_info=True)
        return video
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


async def _render_with_repair(
    runner: _Runner, code: str, entry: str, repair: Repair | None, job_id: uuid.UUID, scene_id: str
) -> tuple[RenderResult | None, str]:
    """Vet+render ``code``, asking ``repair`` for a fix up to ``_MAX_REPAIRS`` times."""
    result, reason = await _vet_and_run(runner, code, entry)
    attempts = 0
    while result is None and repair is not None and attempts < _MAX_REPAIRS:
        attempts += 1
        logger.info("job %s: repairing manim scene %s (%s)", job_id, scene_id, reason)
        try:
            fixed = await repair(code, reason)
        except Exception:
            logger.warning("job %s: manim repair raised for scene %s", job_id, scene_id, exc_info=True)
            break
        if not fixed:
            break
        code = fixed
        result, reason = await _vet_and_run(runner, code, entry)
    return result, reason


async def render_manim_clips(
    storage: Storage,
    job_id: uuid.UUID,
    document: SceneDocument,
    *,
    runner: _Runner | None = None,
    repair: Repair | None = None,
    durations: dict[str, int] | None = None,
    pad: Pad | None = None,
) -> dict[str, str]:
    """Render every manim scene; return {scene_id: mp4 data-URL} for the renderer.
    Also persists each clip + a manifest so the web player can fetch them.

    When a scene's code is unsafe or fails to render and a ``repair`` is given, the
    code + error are sent back for a fix (up to ``_MAX_REPAIRS`` rounds) and
    re-rendered — so a fixable scene becomes a real animation instead of falling back
    to the text stub. A successful clip shorter than its narration (``durations``) is
    freeze-padded to the narration length so the video doesn't end mid-sentence.
    Best-effort throughout: an unrepairable scene is simply skipped, never blocking
    the lesson."""
    runner = runner or ManimRunner()
    pad = pad or _pad_to_ms
    durations = durations or {}
    clips: dict[str, str] = {}
    rendered: list[str] = []

    for scene in document.scenes:
        if scene.kind != SceneKind.manim or not scene.manim_code:
            continue
        result, reason = await _render_with_repair(
            runner, scene.manim_code, scene.manim_entry, repair, job_id, scene.id
        )
        if result is None:
            logger.warning("job %s: manim scene %s unusable (%s), skipping", job_id, scene.id, reason)
            continue
        video = result.video
        target_ms = durations.get(scene.id)
        if target_ms:
            video = await pad(video, target_ms)
        storage.put(scene_manim_key(job_id, scene.id), video)
        clips[scene.id] = MANIM_DATA_URL_PREFIX + base64.b64encode(video).decode()
        rendered.append(scene.id)

    if rendered:
        storage.put(manim_manifest_key(job_id), json.dumps([{"scene_id": s} for s in rendered]).encode())
    return clips
