import uuid
from datetime import datetime
from typing import Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import Column, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel

EMBEDDING_DIM = 1536


def _created_at() -> Any:
    return Field(default=None, sa_column_kwargs={"server_default": func.now()})


class User(SQLModel, table=True):
    __tablename__ = "users"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    email: str = Field(unique=True, index=True)
    name: str
    password_hash: str
    created_at: datetime | None = _created_at()


class Notebook(SQLModel, table=True):
    __tablename__ = "notebooks"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    title: str
    created_at: datetime | None = _created_at()


class Source(SQLModel, table=True):
    __tablename__ = "sources"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    notebook_id: uuid.UUID | None = Field(default=None, foreign_key="notebooks.id")
    type: str
    raw_input: str
    title: str | None = None
    text: str | None = None
    template: str = "explainer"  # lesson visual template (see scenes/templates.py)
    mode: str = "auto"  # course | video | auto (see lesson_mode.py)
    voice: str = "male"  # narration voice: male | female (see voices.py)
    created_at: datetime | None = _created_at()


class Job(SQLModel, table=True):
    __tablename__ = "jobs"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    source_id: uuid.UUID = Field(foreign_key="sources.id")
    status: str = "queued"
    step: str | None = None
    error: str | None = None
    created_at: datetime | None = _created_at()
    updated_at: datetime | None = Field(
        default=None,
        sa_column_kwargs={"server_default": func.now(), "onupdate": func.now()},
    )


class SourceChunk(SQLModel, table=True):
    __tablename__ = "source_chunks"

    id: str = Field(primary_key=True)
    content: str
    embedding: list[float] = Field(sa_column=Column(Vector(EMBEDDING_DIM)))


class Lesson(SQLModel, table=True):
    __tablename__ = "lessons"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    job_id: uuid.UUID = Field(foreign_key="jobs.id")
    source_id: uuid.UUID = Field(foreign_key="sources.id")
    title: str
    summary: str
    key_points: list[Any] = Field(sa_column=Column(JSONB))
    quiz: list[Any] = Field(sa_column=Column(JSONB))
    script: dict[str, Any] = Field(sa_column=Column(JSONB))
    video_url: str | None = None
    created_at: datetime | None = _created_at()


class ProductionRun(SQLModel, table=True):
    __tablename__ = "production_runs"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    job_id: uuid.UUID = Field(foreign_key="jobs.id")
    plan: dict[str, Any] = Field(sa_column=Column(JSONB))
    planner_model: str
    embedding_model: str
    tts_model: str
    engine_version: str
    created_at: datetime | None = _created_at()


class Course(SQLModel, table=True):
    """A multi-module plan for a `course`-mode source. Each module is generated
    into its own lesson (a normal video job) on demand — modules holds
    ``[{order, title, summary, job_id?}]`` with job_id set once generated."""

    __tablename__ = "courses"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    job_id: uuid.UUID = Field(foreign_key="jobs.id", index=True)
    source_id: uuid.UUID = Field(foreign_key="sources.id")
    title: str
    summary: str
    modules: list[Any] = Field(sa_column=Column(JSONB))
    created_at: datetime | None = _created_at()


class MediaAsset(SQLModel, table=True):
    __tablename__ = "media_assets"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    kind: str  # image | icon | illustration
    title: str
    url: str  # external URL, or /media/{key} for uploaded files
    storage_key: str | None = None  # set when the bytes live in our storage
    tags: list[str] = Field(default_factory=list, sa_column=Column(JSONB))
    source: str | None = None  # provider / origin (e.g. "upload", "openverse")
    license: str | None = None
    created_at: datetime | None = _created_at()
