"""The live job pipeline: source -> agentic brain -> SceneDocument -> narration
-> rendered video. Replaces the old plan/code-gen path. All collaborators are
injected (see ``SceneEngines``) so the pipeline is testable without network."""

import base64
import json
import logging
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Protocol

from sqlalchemy.ext.asyncio import AsyncSession

from api.agent_engine.llm import StructuredLLM, structured_llm_from_settings
from api.engines.protocols import Document, SourceLoader, TTSClient
from api.enums import JobStatus
from api.exports import script_markdown, source_markdown
from api.ingestion.loaders import combine_documents, split_sources
from api.logger import short_error
from api.jobs.manim_render import render_manim_clips
from api.jobs.repository import (
    create_lesson_from_scene_document,
    get_job,
    get_source,
    set_lesson_video,
    update_job,
    update_source_content,
)
from api.scenes.art_director import art_direct
from api.scenes.quiz import build_quiz
from api.scenes.schema import SceneDocument
from api.scenes.templates import Template, get_template
from api.storage import Storage
from api.storage_keys import (
    AUDIO_DATA_URL_PREFIX,
    audio_manifest_key,
    lesson_video_key,
    scene_audio_key,
    script_markdown_key,
    source_markdown_key,
)
from api.tts_delivery import prosody_for
from api.voices import voice_name

logger = logging.getLogger("api.pipeline")


class SceneBrain(Protocol):
    async def generate(
        self,
        source_text: str,
        source_title: str,
        template: "Template | None" = None,
        mode: str = "auto",
    ) -> SceneDocument: ...


class SceneRenderer(Protocol):
    async def render(
        self,
        document: SceneDocument,
        audio: list[dict[str, Any]],
        manim_clips: dict[str, str] | None = None,
    ) -> bytes: ...


@dataclass
class SceneEngines:
    select_loader: Callable[[str], SourceLoader]
    brain: SceneBrain
    tts: TTSClient
    scene_render: SceneRenderer
    storage: Storage


async def run_scene_pipeline(
    session: AsyncSession, job_id: uuid.UUID, engines: SceneEngines
) -> None:
    job = await get_job(session, job_id)
    if job is None:
        raise ValueError(f"job {job_id} not found")
    source = await get_source(session, job.source_id)
    if source is None:
        raise ValueError(f"source {job.source_id} not found")
    source_id = source.id
    raw_input = source.raw_input

    try:
        await update_job(session, job_id, status=JobStatus.loading, step="loading source")
        # raw_input may hold several sources (links/videos/text). Load each and
        # combine into one document; skip individual failures so one dead URL
        # doesn't sink a multi-source lesson.
        parts = split_sources(raw_input)
        loaded: list[Document] = []
        last_err: Exception | None = None
        for part in parts:
            try:
                loaded.append(await engines.select_loader(part).load(part))
            except Exception as exc:
                last_err = exc
                logger.warning("job %s: source failed to load: %s", job_id, exc)
        if not loaded:
            raise last_err or ValueError("no source could be loaded")
        document = combine_documents(loaded)
        await update_source_content(session, source_id, text=document.text, title=document.title)
        # Archive the extracted source (e.g. YouTube transcript) as Markdown.
        engines.storage.put(source_markdown_key(job_id), source_markdown(document).encode())

        await update_job(session, job_id, status=JobStatus.planning, step="designing the lesson")
        # The template shapes generation (voice, density, diagram bias, delivery)
        # AND paints the final theme — so a marketing run and a whiteboard run of
        # the same source produce genuinely different lessons, not just recolours.
        template = get_template(source.template)
        scene_doc = await engines.brain.generate(
            document.text, document.title or "", template, source.mode
        )
        # Theme paints the look; the lesson mode picks the motion profile —
        # course studies better as restrained "slide" motion, video gets the full
        # animated treatment.
        profile = "slide" if source.mode == "course" else "video"
        scene_doc = scene_doc.model_copy(update={"theme": template.theme, "profile": profile})
        # Art direction: an LLM art-director picks each plain slide's layout +
        # visual (rule-based fallback when no model is configured). Best-effort.
        try:
            art_llm: StructuredLLM | None = structured_llm_from_settings()
        except Exception:
            art_llm = None
        scene_doc = await art_direct(session, scene_doc, template, llm=art_llm)
        # Comprehension quiz from the lesson content (best-effort; reuses the
        # art-director's LLM, empty when no model is configured).
        quiz = await build_quiz(scene_doc, art_llm)
        lesson = await create_lesson_from_scene_document(
            session, job_id, source_id, scene_doc, quiz=quiz
        )
        # Archive the narration script as Markdown.
        engines.storage.put(script_markdown_key(job_id), script_markdown(scene_doc).encode())
        logger.info("job %s: %d scenes", job_id, len(scene_doc.scenes))

        # The lesson is viewable from here on: the web player renders the
        # SceneDocument directly. Narration audio and the MP4 export are
        # enhancements, so a down TTS or render service must not fail the job.
        await update_job(session, job_id, status=JobStatus.narrating, step="synthesizing narration")
        voice = voice_name(source.voice)  # male / female narrator chosen at creation
        audio_tracks: list[dict[str, Any]] = []
        for scene in scene_doc.scenes:
            # Narrate each scene independently so one transient TTS failure
            # doesn't cost the whole lesson its voice-over. Delivery tone →
            # voice prosody so the narration sounds lively, not flat.
            rate, pitch = prosody_for(scene.narration.delivery)
            try:
                result = await engines.tts.synthesize(
                    scene.narration.text, rate=rate, pitch=pitch, voice=voice
                )
            except Exception:
                logger.warning(
                    "job %s: narration failed for scene %s, skipping", job_id, scene.id, exc_info=True
                )
                continue
            if not result.audio:
                continue
            engines.storage.put(scene_audio_key(job_id, scene.id), result.audio)
            words = [
                {"text": w.text, "start_ms": w.start_ms, "end_ms": w.end_ms} for w in result.words
            ]
            audio_tracks.append(
                {
                    "scene_id": scene.id,
                    "url": AUDIO_DATA_URL_PREFIX + base64.b64encode(result.audio).decode(),
                    "duration_ms": result.duration_ms,
                    "words": words,
                }
            )

        # Persist a small manifest so the web player can play per-scene narration,
        # size its timeline to the audio, and highlight words as they're spoken
        # (the data-URLs above go to the renderer).
        if audio_tracks:
            manifest = [
                {"scene_id": t["scene_id"], "duration_ms": t["duration_ms"], "words": t["words"]}
                for t in audio_tracks
            ]
            engines.storage.put(audio_manifest_key(job_id), json.dumps(manifest).encode())

        # Render any math/explainer scenes to Manim clips (best-effort: failures
        # fall back to the on-screen narration stub, never blocking the lesson).
        manim_clips = await render_manim_clips(engines.storage, job_id, scene_doc)
        if manim_clips:
            logger.info("job %s: %d manim clips", job_id, len(manim_clips))

        await update_job(session, job_id, status=JobStatus.rendering, step="rendering video")
        try:
            video = await engines.scene_render.render(scene_doc, audio_tracks, manim_clips)
            video_ref = engines.storage.put(lesson_video_key(job_id), video)
            await set_lesson_video(session, lesson.id, video_ref)
        except Exception:
            logger.warning("job %s: mp4 render unavailable, continuing", job_id, exc_info=True)

        await update_job(session, job_id, status=JobStatus.done, step="done")
    except Exception as exc:
        logger.exception("job %s failed", job_id)
        # A DB error would have aborted this session's transaction, so the reads/writes
        # below would fail too and leave the job stuck "in progress" forever. Roll back
        # first to clear that state; prior status updates already committed per call.
        try:
            await session.rollback()
            current = await get_job(session, job_id)
            step = current.step if current else None
            await update_job(session, job_id, status=JobStatus.failed, step=step, error=short_error(exc))
        except Exception:
            logger.exception("job %s: failed to record failure status", job_id)
