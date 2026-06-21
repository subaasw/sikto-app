import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from api.agent.retrieval import EmbeddingRetriever
from api.chat.engine import GroundedChat
from api.db import get_session
from api.jobs.repository import (
    create_notebook,
    create_source_and_job,
    get_notebook,
    list_notebook_source_ids,
)
from api.knowledge.embeddings import embeddings_client_from_settings
from api.knowledge.vector_store import PgVectorStore
from api.models import Notebook
from api.visuals.llm import chat_llm_from_settings

router = APIRouter(tags=["notebooks"])


class CreateNotebookRequest(BaseModel):
    title: str


class NotebookResponse(BaseModel):
    id: uuid.UUID
    title: str
    source_ids: list[str]


class AddSourceRequest(BaseModel):
    type: str
    input: str


class CreateSourceResponse(BaseModel):
    job_id: uuid.UUID


class ChatRequest(BaseModel):
    question: str


class CitationResponse(BaseModel):
    source_id: str
    content: str
    score: float


class ChatResponse(BaseModel):
    answer: str
    citations: list[CitationResponse]


async def _require_notebook(notebook_id: uuid.UUID, session: AsyncSession) -> Notebook:
    notebook = await get_notebook(session, notebook_id)
    if notebook is None:
        raise HTTPException(status_code=404, detail="notebook not found")
    return notebook


@router.post("/notebooks", status_code=201, response_model=NotebookResponse)
async def create(
    body: CreateNotebookRequest, session: AsyncSession = Depends(get_session)
) -> NotebookResponse:
    notebook = await create_notebook(session, body.title)
    return NotebookResponse(id=notebook.id, title=notebook.title, source_ids=[])


@router.get("/notebooks/{notebook_id}", response_model=NotebookResponse)
async def read(
    notebook_id: uuid.UUID, session: AsyncSession = Depends(get_session)
) -> NotebookResponse:
    notebook = await _require_notebook(notebook_id, session)
    source_ids = await list_notebook_source_ids(session, notebook_id)
    return NotebookResponse(id=notebook.id, title=notebook.title, source_ids=source_ids)


@router.post(
    "/notebooks/{notebook_id}/sources", status_code=201, response_model=CreateSourceResponse
)
async def add_source(
    notebook_id: uuid.UUID,
    body: AddSourceRequest,
    session: AsyncSession = Depends(get_session),
) -> CreateSourceResponse:
    await _require_notebook(notebook_id, session)
    job = await create_source_and_job(
        session, source_type=body.type, raw_input=body.input, notebook_id=notebook_id
    )
    return CreateSourceResponse(job_id=job.id)


@router.post("/notebooks/{notebook_id}/chat", response_model=ChatResponse)
async def notebook_chat(
    notebook_id: uuid.UUID,
    body: ChatRequest,
    session: AsyncSession = Depends(get_session),
) -> ChatResponse:
    await _require_notebook(notebook_id, session)
    source_ids = await list_notebook_source_ids(session, notebook_id)
    retriever = EmbeddingRetriever(embeddings_client_from_settings(), PgVectorStore(), source_ids)
    result = await GroundedChat(retriever, chat_llm_from_settings()).answer(body.question)
    return ChatResponse(
        answer=result.answer,
        citations=[
            CitationResponse(source_id=p.source_id, content=p.content, score=p.score)
            for p in result.citations
        ],
    )
