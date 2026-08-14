import asyncio
import json
import os
import uuid
from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from api.agent.catalog import model_choices
from api.auth import OptionalUser
from api.config import Settings, get_settings
from api.db import SessionLocal, get_session
from api.ingestion.documents import DOCUMENT_EXTENSIONS
from api.ingestion.loaders import SOURCE_SEP
from api.jobs.repository import create_source_and_job, get_job, list_recent_jobs
from api.lesson_mode import DEFAULT_MODE, MODES
from api.scenes.templates import DEFAULT_TEMPLATE, TEMPLATES
from api.storage import LocalStorage
from api.voices import DEFAULT_VOICE, VOICES

router = APIRouter(tags=["sources"])


class CreateSourceRequest(BaseModel):
    type: str
    input: str = ""  # single source (back-compat); ignored when `inputs` is set
    inputs: list[str] = []  # several sources (links/videos/text) → one combined lesson
    template: str = DEFAULT_TEMPLATE
    mode: str = DEFAULT_MODE
    voice: str = DEFAULT_VOICE
    model: str | None = None

    def combined_input(self) -> str:
        sources = self.inputs or [self.input]
        return SOURCE_SEP.join(s.strip() for s in sources if s.strip())


class CreateSourceResponse(BaseModel):
    job_id: uuid.UUID


class UploadedDocument(BaseModel):
    path: str
    name: str


class JobResponse(BaseModel):
    id: uuid.UUID
    status: str
    step: str | None
    error: str | None


@router.post("/sources", status_code=201, response_model=CreateSourceResponse)
async def create_source(
    body: CreateSourceRequest,
    user: OptionalUser = None,
    settings: Settings = Depends(get_settings),
    session: AsyncSession = Depends(get_session),
) -> CreateSourceResponse:
    template = body.template if body.template in TEMPLATES else DEFAULT_TEMPLATE
    mode = body.mode if body.mode in MODES else DEFAULT_MODE
    voice = body.voice if body.voice in VOICES else DEFAULT_VOICE
    model = body.model if body.model in model_choices(settings) else None
    raw_input = body.combined_input()
    if not raw_input:
        raise HTTPException(status_code=422, detail="at least one source is required")
    job = await create_source_and_job(
        session,
        source_type=body.type,
        raw_input=raw_input,
        template=template,
        mode=mode,
        voice=voice,
        model=model,
        user_id=user.id if user else None,
    )
    return CreateSourceResponse(job_id=job.id)


@router.post("/sources/upload", status_code=201, response_model=list[UploadedDocument])
async def upload_source_documents(
    files: list[UploadFile] = File(...),
) -> list[UploadedDocument]:
    """Upload PDFs/slides/docs to use as lesson sources. Each file is stored as-is;
    MarkItDown converts it to markdown when the job runs (api.ingestion.documents)."""
    storage = LocalStorage(get_settings().storage_dir)
    out: list[UploadedDocument] = []
    for file in files:
        ext = os.path.splitext(file.filename or "")[1].lower()
        if ext not in DOCUMENT_EXTENSIONS:
            raise HTTPException(
                status_code=422, detail=f"unsupported file type: {ext or file.filename}"
            )
        data = await file.read()
        if not data:
            continue  # skip empties rather than failing the whole batch
        key = f"documents/{uuid.uuid4().hex}{ext}"
        storage.put(key, data)
        out.append(UploadedDocument(path=str(storage.root / key), name=file.filename or "Upload"))
    if not out:
        raise HTTPException(status_code=422, detail="no usable files")
    return out


@router.get("/jobs/{job_id}", response_model=JobResponse)
async def read_job(job_id: uuid.UUID, session: AsyncSession = Depends(get_session)) -> JobResponse:
    job = await get_job(session, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="job not found")
    return JobResponse(id=job.id, status=job.status, step=job.step, error=job.error)


_TERMINAL = {"done", "failed"}


@router.get("/jobs/{job_id}/stream")
async def stream_job(job_id: uuid.UUID, request: Request) -> StreamingResponse:
    """Server-Sent Events: one long-lived connection in place of second-by-second
    polling. We watch the job row (written by the worker process) and push only
    when status/step/error changes, then close once the job is done or failed.

    ponytail: server-side DB poll every 1s — correct across the worker/api process
    boundary; swap for Postgres LISTEN/NOTIFY only if job volume makes it bite."""

    async def events():
        last: tuple[str, str | None, str | None] | None = None
        for _ in range(600):  # ~10 min ceiling so a stuck job can't pin a connection
            if await request.is_disconnected():
                return
            async with SessionLocal() as session:
                job = await get_job(session, job_id)
                if job is None:
                    yield 'event: error\ndata: {"detail":"job not found"}\n\n'
                    return
                snapshot = (job.status, job.step, job.error)
                payload = json.dumps(
                    {"id": str(job.id), "status": job.status, "step": job.step, "error": job.error}
                )
            if snapshot != last:
                last = snapshot
                yield f"data: {payload}\n\n"
            if snapshot[0] in _TERMINAL:
                return
            await asyncio.sleep(1.0)

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/events")
async def stream_events(request: Request, user: OptionalUser = None) -> StreamingResponse:
    """App-wide job stream: every job update for the current user on one
    connection, so the UI keeps live progress while navigating anywhere."""
    user_id = user.id if user else None

    async def events() -> AsyncIterator[str]:
        seen: dict[uuid.UUID, tuple[str, str | None, str | None]] = {}
        for _ in range(600):
            if await request.is_disconnected():
                return
            async with SessionLocal() as session:
                jobs = await list_recent_jobs(session, user_id)
                payloads = [
                    (
                        job.id,
                        (job.status, job.step, job.error),
                        json.dumps(
                            {
                                "id": str(job.id),
                                "status": job.status,
                                "step": job.step,
                                "error": job.error,
                            }
                        ),
                    )
                    for job in jobs
                ]
            for job_id, snapshot, payload in payloads:
                if seen.get(job_id) != snapshot:
                    seen[job_id] = snapshot
                    yield f"data: {payload}\n\n"
            await asyncio.sleep(1.0)

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
