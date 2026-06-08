import uuid

from sqlalchemy import select

from api import __version__
from api.agent.engine import AgentPlanner, MicrolearningAgent
from api.agent.llm import tool_calling_llm_from_settings
from api.agent.retrieval import EmbeddingRetriever
from api.config import get_settings
from api.db import SessionLocal
from api.engines.clients import remotion_code_client_from_settings, tts_client_from_settings
from api.enums import JobStatus
from api.ingestion.registry import select_loader
from api.jobs.pipeline import Engines, run_pipeline
from api.knowledge.embeddings import embeddings_client_from_settings
from api.knowledge.vector_store import PgVectorStore
from api.models import Job
from api.planning.schema import Retrieval, RetrievalStrategy, VectorStoreName, Voice
from api.sandbox.manim import ManimRunner
from api.storage import LocalStorage
from api.visuals.assembler import Assembler
from api.visuals.coder import VisualCoder
from api.visuals.llm import chat_llm_from_settings
from api.visuals.renderer import SegmentRenderer


def default_engines() -> Engines:
    settings = get_settings()
    embeddings = embeddings_client_from_settings()
    vectors = PgVectorStore()
    agent = MicrolearningAgent(
        tool_calling_llm_from_settings(),
        EmbeddingRetriever(embeddings, vectors),
        voice=Voice(id=settings.tts_voice, language=settings.tts_language),
        retrieval=Retrieval(strategy=RetrievalStrategy.vector, store=VectorStoreName.pgvector),
        planner_model=settings.planner_model,
        embedding_model=settings.embedding_model,
        tts_model=settings.tts_model,
        engine_version=__version__,
    )
    remotion = remotion_code_client_from_settings()
    segment_renderer = SegmentRenderer(
        VisualCoder(chat_llm_from_settings()), ManimRunner(), remotion.render
    )
    return Engines(
        select_loader=select_loader,
        embeddings=embeddings,
        vectors=vectors,
        planner=AgentPlanner(agent),
        tts=tts_client_from_settings(),
        segment_renderer=segment_renderer,
        assembler=Assembler(),
        storage=LocalStorage(settings.storage_dir),
    )


async def process_next_job() -> uuid.UUID | None:
    async with SessionLocal() as session:
        result = await session.execute(select(Job).where(Job.status == JobStatus.queued).limit(1))
        job = result.scalar_one_or_none()
        if job is None:
            return None
        await run_pipeline(session, job.id, default_engines())
        return job.id
