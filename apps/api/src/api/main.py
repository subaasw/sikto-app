from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api import __version__
from api.config import get_settings
from api.routers import chat, health, lessons, notebooks, sources

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version=__version__,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(sources.router)
app.include_router(lessons.router)
app.include_router(chat.router)
app.include_router(notebooks.router)


@app.get("/")
def root() -> dict[str, str]:
    return {"service": settings.app_name, "version": __version__}
