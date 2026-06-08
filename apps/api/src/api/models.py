import uuid
from datetime import datetime
from typing import Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import ForeignKey, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

EMBEDDING_DIM = 1536


class Base(DeclarativeBase):
    pass


class Notebook(Base):
    __tablename__ = "notebooks"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    title: Mapped[str]
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class Source(Base):
    __tablename__ = "sources"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    notebook_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("notebooks.id"))
    type: Mapped[str]
    raw_input: Mapped[str]
    title: Mapped[str | None]
    text: Mapped[str | None]
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    source_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("sources.id"))
    status: Mapped[str] = mapped_column(default="queued")
    step: Mapped[str | None]
    error: Mapped[str | None]
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())


class SourceChunk(Base):
    __tablename__ = "source_chunks"

    id: Mapped[str] = mapped_column(primary_key=True)
    content: Mapped[str]
    embedding: Mapped[list[float]] = mapped_column(Vector(EMBEDDING_DIM))


class Lesson(Base):
    __tablename__ = "lessons"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    job_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("jobs.id"))
    source_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("sources.id"))
    title: Mapped[str]
    summary: Mapped[str]
    key_points: Mapped[list[Any]] = mapped_column(JSONB)
    quiz: Mapped[list[Any]] = mapped_column(JSONB)
    script: Mapped[dict[str, Any]] = mapped_column(JSONB)
    video_url: Mapped[str | None]
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class ProductionRun(Base):
    __tablename__ = "production_runs"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    job_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("jobs.id"))
    plan: Mapped[dict[str, Any]] = mapped_column(JSONB)
    planner_model: Mapped[str]
    embedding_model: Mapped[str]
    tts_model: Mapped[str]
    engine_version: Mapped[str]
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
