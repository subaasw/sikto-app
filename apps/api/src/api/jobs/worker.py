import asyncio
import logging
import uuid

from sqlalchemy import select
from sqlmodel import col

from api.agent_engine.graph import AgentBrain
from api.config import get_settings
from api.db import SessionLocal
from api.engines.clients import scene_render_client_from_settings, tts_client_from_settings
from api.enums import JobStatus
from api.ingestion.registry import select_loader
from api.jobs.scene_pipeline import SceneEngines, run_scene_pipeline
from api.models import Job
from api.storage import LocalStorage

logger = logging.getLogger("api.worker")


def default_scene_engines() -> SceneEngines:
    settings = get_settings()
    return SceneEngines(
        select_loader=select_loader,
        brain=AgentBrain(),
        tts=tts_client_from_settings(),
        scene_render=scene_render_client_from_settings(),
        storage=LocalStorage(settings.storage_dir),
    )


async def process_next_job() -> uuid.UUID | None:
    async with SessionLocal() as session:
        result = await session.execute(
            select(Job)
            .where(col(Job.status) == JobStatus.queued)
            .order_by(col(Job.created_at))
            .limit(1)
        )
        job: Job | None = result.scalar_one_or_none()
        if job is None:
            return None
        await run_scene_pipeline(session, job.id, default_scene_engines())
        return job.id


async def run_worker_loop(poll_interval: float = 2.0) -> None:
    """Continuously drain queued jobs. Runs in-process as a background task started
    from the API lifespan, so ``make run`` alone is enough to process lessons. Each
    iteration handles at most one job; when the queue is empty we sleep briefly. The
    loop never dies on a job error — those are recorded on the job itself."""
    logger.info("job worker started")
    while True:
        try:
            job_id = await process_next_job()
        except asyncio.CancelledError:
            logger.info("job worker stopping")
            raise
        except Exception:
            logger.exception("worker loop iteration failed")
            job_id = None
        if job_id is None:
            await asyncio.sleep(poll_interval)
