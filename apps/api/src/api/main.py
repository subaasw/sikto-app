import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager, suppress
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from api import __version__
from api.auth import register_auth_error_handler
from api.config import get_settings
from api.db import check_connection, engine
from api.jobs.worker import run_worker_loop
from api.logger import add_request_logging, configure_logging, register_exception_handlers
from api.routers import (
    assets,
    auth,
    chat,
    courses,
    health,
    lessons,
    notebooks,
    sources,
    templates,
)

settings = get_settings()
configure_logging(settings)
logger = logging.getLogger("api")


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    # Startup: fail fast if the database is unreachable.
    try:
        await check_connection()
    except Exception as exc:
        raise RuntimeError(
            f"database connection failed at startup ({settings.database_url}): {exc}"
        ) from exc
    logger.info("database connection ok")

    # Start the in-process job worker so queued lessons are processed.
    worker_task: asyncio.Task[None] | None = None
    if settings.run_worker:
        worker_task = asyncio.create_task(run_worker_loop())

    yield

    # Graceful shutdown: stop the worker, then drain and close the pool.
    if worker_task is not None:
        worker_task.cancel()
        with suppress(asyncio.CancelledError):
            await worker_task
    await engine.dispose()
    logger.info("database engine disposed")


app = FastAPI(
    title=settings.app_name,
    version=__version__,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

add_request_logging(app)
register_auth_error_handler(app)
register_exception_handlers(app)

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(sources.router)
app.include_router(lessons.router)
app.include_router(chat.router)
app.include_router(notebooks.router)
app.include_router(templates.router)
app.include_router(assets.router)
app.include_router(courses.router)

# Serve rendered videos and audio from local storage (Starlette's StaticFiles
# supports HTTP range requests, so videos seek correctly in the browser).
_storage_root = Path(settings.storage_dir)
_storage_root.mkdir(parents=True, exist_ok=True)
app.mount("/media", StaticFiles(directory=_storage_root), name="media")


@app.get("/")
def root() -> dict[str, str]:
    return {"service": settings.app_name, "version": __version__}
