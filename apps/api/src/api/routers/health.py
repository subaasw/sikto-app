from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlmodel.ext.asyncio.session import AsyncSession

from api import __version__
from api.config import get_settings
from api.db import get_session

router = APIRouter(prefix="/health", tags=["health"])


@router.get("")
def health() -> dict[str, str]:
    """Liveness: the process is up. Does not touch the database."""
    settings = get_settings()
    return {
        "status": "ok",
        "service": settings.app_name,
        "version": __version__,
    }


@router.get("/ready")
async def readiness(session: Annotated[AsyncSession, Depends(get_session)]) -> dict[str, str]:
    """Readiness: verifies the database is reachable on each call."""
    try:
        await session.execute(text("SELECT 1"))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="database unavailable"
        ) from exc
    return {"status": "ready"}
