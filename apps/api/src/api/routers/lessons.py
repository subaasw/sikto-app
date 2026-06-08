import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from api.db import get_session
from api.jobs.repository import get_lesson_by_job

router = APIRouter(tags=["lessons"])


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
    quiz: list[QuizItemResponse]


@router.get("/lessons/{job_id}", response_model=LessonResponse)
async def read_lesson(
    job_id: uuid.UUID, session: AsyncSession = Depends(get_session)
) -> LessonResponse:
    lesson = await get_lesson_by_job(session, job_id)
    if lesson is None:
        raise HTTPException(status_code=404, detail="lesson not found")
    return LessonResponse(
        id=lesson.id,
        title=lesson.title,
        summary=lesson.summary,
        key_points=list(lesson.key_points),
        video_url=lesson.video_url,
        quiz=[QuizItemResponse(**item) for item in lesson.quiz],
    )
