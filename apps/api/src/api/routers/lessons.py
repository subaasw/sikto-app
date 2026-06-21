import json
import uuid
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from api.config import get_settings
from api.db import get_session
from api.jobs.repository import get_lesson_by_job, list_lessons
from api.storage import LocalStorage
from api.storage_keys import (
    audio_manifest_key,
    manim_manifest_key,
    scene_audio_key,
    scene_manim_key,
    script_markdown_key,
    source_markdown_key,
)

router = APIRouter(tags=["lessons"])


def _media_url(request: Request, ref: str | None) -> str | None:
    """Turn a stored object key into an absolute URL served by ``/media``."""
    if not ref:
        return None
    return str(request.base_url).rstrip("/") + "/media/" + ref.lstrip("/")


class QuizItemResponse(BaseModel):
    question: str
    choices: list[str] | None = None
    answer: str
    explanation: str


class LessonResponse(BaseModel):
    id: uuid.UUID
    title: str
    summary: str
    key_points: list[str]
    video_url: str | None
    transcript_url: str | None
    script_url: str | None
    quiz: list[QuizItemResponse]


class LessonSummary(BaseModel):
    """A lesson card for the library/history list. ``job_id`` is the route key."""

    job_id: uuid.UUID
    title: str
    summary: str
    has_video: bool
    created_at: datetime | None


@router.get("/lessons", response_model=list[LessonSummary])
async def list_history(session: AsyncSession = Depends(get_session)) -> list[LessonSummary]:
    lessons = await list_lessons(session)
    return [
        LessonSummary(
            job_id=lesson.job_id,
            title=lesson.title,
            summary=lesson.summary,
            has_video=bool(lesson.video_url),
            created_at=lesson.created_at,
        )
        for lesson in lessons
    ]


@router.get("/lessons/{job_id}", response_model=LessonResponse)
async def read_lesson(
    job_id: uuid.UUID, request: Request, session: AsyncSession = Depends(get_session)
) -> LessonResponse:
    lesson = await get_lesson_by_job(session, job_id)
    if lesson is None:
        raise HTTPException(status_code=404, detail="lesson not found")
    storage = LocalStorage(get_settings().storage_dir)

    def md_url(key: str) -> str | None:
        return _media_url(request, key) if storage.exists(key) else None

    return LessonResponse(
        id=lesson.id,
        title=lesson.title,
        summary=lesson.summary,
        key_points=list(lesson.key_points),
        video_url=_media_url(request, lesson.video_url),
        transcript_url=md_url(source_markdown_key(job_id)),
        script_url=md_url(script_markdown_key(job_id)),
        quiz=[QuizItemResponse(**item) for item in lesson.quiz],
    )


@router.get("/lessons/{job_id}/scene-document")
async def read_scene_document(
    job_id: uuid.UUID, session: AsyncSession = Depends(get_session)
) -> dict[str, Any]:
    """The declarative SceneDocument backing a lesson (for the player/editor)."""
    lesson = await get_lesson_by_job(session, job_id)
    if lesson is None:
        raise HTTPException(status_code=404, detail="lesson not found")
    return dict(lesson.script)


class WordTimingResponse(BaseModel):
    text: str
    start_ms: int
    end_ms: int


class SceneAudioResponse(BaseModel):
    scene_id: str
    url: str
    duration_ms: int
    words: list[WordTimingResponse] = []


@router.get("/lessons/{job_id}/audio", response_model=list[SceneAudioResponse])
async def read_lesson_audio(
    job_id: uuid.UUID, request: Request, session: AsyncSession = Depends(get_session)
) -> list[SceneAudioResponse]:
    """Per-scene narration tracks for the web player. Empty when TTS didn't run."""
    lesson = await get_lesson_by_job(session, job_id)
    if lesson is None:
        raise HTTPException(status_code=404, detail="lesson not found")
    storage = LocalStorage(get_settings().storage_dir)
    manifest_key = audio_manifest_key(job_id)
    if not storage.exists(manifest_key):
        return []
    entries = json.loads(storage.get(manifest_key))
    return [
        SceneAudioResponse(
            scene_id=entry["scene_id"],
            url=_media_url(request, scene_audio_key(job_id, entry["scene_id"])) or "",
            duration_ms=int(entry["duration_ms"]),
            words=[WordTimingResponse(**w) for w in entry.get("words") or []],
        )
        for entry in entries
    ]


class SceneManimResponse(BaseModel):
    scene_id: str
    url: str


@router.get("/lessons/{job_id}/manim", response_model=list[SceneManimResponse])
async def read_lesson_manim(
    job_id: uuid.UUID, request: Request, session: AsyncSession = Depends(get_session)
) -> list[SceneManimResponse]:
    """Per-scene Manim clip URLs for the web player. Empty when no clips rendered."""
    lesson = await get_lesson_by_job(session, job_id)
    if lesson is None:
        raise HTTPException(status_code=404, detail="lesson not found")
    storage = LocalStorage(get_settings().storage_dir)
    manifest_key = manim_manifest_key(job_id)
    if not storage.exists(manifest_key):
        return []
    entries = json.loads(storage.get(manifest_key))
    return [
        SceneManimResponse(
            scene_id=entry["scene_id"],
            url=_media_url(request, scene_manim_key(job_id, entry["scene_id"])) or "",
        )
        for entry in entries
    ]
