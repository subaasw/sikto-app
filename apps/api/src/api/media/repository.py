"""Data access for the media library (collected images / icons / illustrations)."""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col

from api.models import MediaAsset


async def create_media_asset(
    session: AsyncSession,
    *,
    kind: str,
    title: str,
    url: str,
    storage_key: str | None = None,
    tags: list[str] | None = None,
    source: str | None = None,
    license: str | None = None,
) -> MediaAsset:
    asset = MediaAsset(
        kind=kind,
        title=title,
        url=url,
        storage_key=storage_key,
        tags=tags or [],
        source=source,
        license=license,
    )
    session.add(asset)
    await session.commit()
    await session.refresh(asset)
    return asset


async def list_media_assets(
    session: AsyncSession, *, kind: str | None = None, query: str | None = None, limit: int = 200
) -> list[MediaAsset]:
    stmt = select(MediaAsset).order_by(col(MediaAsset.created_at).desc()).limit(limit)
    if kind:
        stmt = stmt.where(col(MediaAsset.kind) == kind)
    result = await session.execute(stmt)
    assets = list(result.scalars().all())
    if query:
        q = query.lower()
        assets = [a for a in assets if q in a.title.lower() or any(q in t.lower() for t in a.tags)]
    return assets


async def search_media_assets(
    session: AsyncSession, *, tags: list[str], kind: str | None = None, limit: int = 12
) -> list[MediaAsset]:
    """Tag-based lookup for the AI: assets whose tags overlap the wanted ones,
    ranked by how many match."""
    wanted = {t.lower() for t in tags if t}
    candidates = await list_media_assets(session, kind=kind, limit=500)
    scored = [
        (sum(1 for t in a.tags if t.lower() in wanted), a)
        for a in candidates
    ]
    hits = [a for score, a in sorted(scored, key=lambda s: s[0], reverse=True) if score > 0]
    return hits[:limit]


async def get_media_asset(session: AsyncSession, asset_id: uuid.UUID) -> MediaAsset | None:
    return await session.get(MediaAsset, asset_id)


async def delete_media_asset(session: AsyncSession, asset_id: uuid.UUID) -> bool:
    asset = await session.get(MediaAsset, asset_id)
    if asset is None:
        return False
    await session.delete(asset)
    await session.commit()
    return True
