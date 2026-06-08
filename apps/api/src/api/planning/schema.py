from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class Difficulty(StrEnum):
    intro = "intro"
    intermediate = "intermediate"
    advanced = "advanced"


class VisualType(StrEnum):
    title = "title"
    bullet = "bullet"
    talking_point = "talking-point"
    equation = "equation"
    diagram = "diagram"
    code = "code"


class RetrievalStrategy(StrEnum):
    direct = "direct"
    vector = "vector"


class VectorStoreName(StrEnum):
    pgvector = "pgvector"
    chroma = "chroma"


class QuizItem(BaseModel):
    question: str
    choices: list[str] | None = None
    answer: str
    explanation: str


class Segment(BaseModel):
    id: str
    order: int
    narration: str
    caption: str
    visual_type: VisualType
    render_hints: dict[str, Any] = Field(default_factory=dict)
    estimated_duration_ms: int | None = None


class Voice(BaseModel):
    id: str
    language: str
    speed: float | None = None
    pitch: float | None = None
    style: str | None = None


class Lesson(BaseModel):
    title: str
    summary: str
    difficulty: Difficulty
    key_points: list[str] = Field(min_length=3, max_length=5)
    quiz: list[QuizItem] = Field(min_length=2, max_length=3)


class Retrieval(BaseModel):
    strategy: RetrievalStrategy
    store: VectorStoreName
    k: int | None = None


class PlanMeta(BaseModel):
    source_ids: list[str]
    planner_model: str
    embedding_model: str
    tts_model: str
    engine_version: str


class ProductionPlan(BaseModel):
    lesson: Lesson
    voice: Voice
    segments: list[Segment] = Field(min_length=1)
    retrieval: Retrieval
    meta: PlanMeta


class PlanDraft(BaseModel):
    """The subset the LLM produces; the engine supplies voice, retrieval, and meta."""

    lesson: Lesson
    segments: list[Segment] = Field(min_length=1)
