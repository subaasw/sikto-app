"""The media library API. Mounted at /assets (the /media path is the static
file mount that serves stored bytes)."""

import os
import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from api.config import get_settings
from api.db import get_session
from api.media.providers import search_online
from api.media.repository import (
    create_media_asset,
    delete_media_asset,
    list_media_assets,
)
from api.models import MediaAsset
from api.storage import LocalStorage

router = APIRouter(tags=["media"])

ALLOWED_KINDS = {"image", "icon", "illustration"}


class MediaAssetResponse(BaseModel):
    id: uuid.UUID
    kind: str
    title: str
    url: str
    tags: list[str]
    source: str | None
    license: str | None


class CreateAssetRequest(BaseModel):
    kind: str = "image"
    title: str
    url: str
    tags: list[str] = []
    source: str | None = "url"
    license: str | None = None


def _to_response(request: Request, asset: MediaAsset) -> MediaAssetResponse:
    if asset.storage_key:
        base = str(request.base_url).rstrip("/")
        url = f"{base}/media/{asset.storage_key}"
    else:
        url = asset.url
    return MediaAssetResponse(
        id=asset.id,
        kind=asset.kind,
        title=asset.title,
        url=url,
        tags=asset.tags,
        source=asset.source,
        license=asset.license,
    )


class MediaSearchResult(BaseModel):
    title: str
    url: str
    thumbnail: str
    source: str
    kind: str
    license: str | None = None
    tags: list[str] = []


@router.get("/assets/search", response_model=list[MediaSearchResult])
async def search_assets(q: str, kind: str = "image") -> list[MediaSearchResult]:
    """Search free online providers (Iconify icons / Openverse images). Results
    aren't saved — import the ones you want via POST /assets."""
    results = await search_online(q, "icon" if kind == "icon" else "image")
    return [
        MediaSearchResult(
            title=r.title,
            url=r.url,
            thumbnail=r.thumbnail,
            source=r.source,
            kind=r.kind,
            license=r.license,
            tags=r.tags,
        )
        for r in results
    ]


@router.get("/assets", response_model=list[MediaAssetResponse])
async def list_assets(
    request: Request,
    kind: str | None = None,
    q: str | None = None,
    session: AsyncSession = Depends(get_session),
) -> list[MediaAssetResponse]:
    assets = await list_media_assets(session, kind=kind, query=q)
    return [_to_response(request, a) for a in assets]


@router.post("/assets", status_code=201, response_model=MediaAssetResponse)
async def add_asset(
    body: CreateAssetRequest, request: Request, session: AsyncSession = Depends(get_session)
) -> MediaAssetResponse:
    if body.kind not in ALLOWED_KINDS:
        raise HTTPException(status_code=422, detail=f"kind must be one of {sorted(ALLOWED_KINDS)}")
    asset = await create_media_asset(
        session,
        kind=body.kind,
        title=body.title.strip() or "Untitled",
        url=body.url,
        tags=[t.strip() for t in body.tags if t.strip()],
        source=body.source,
        license=body.license,
    )
    return _to_response(request, asset)


@router.post("/assets/upload", status_code=201, response_model=MediaAssetResponse)
async def upload_asset(
    request: Request,
    file: UploadFile = File(...),
    title: str = Form(""),
    kind: str = Form("image"),
    tags: str = Form(""),
    session: AsyncSession = Depends(get_session),
) -> MediaAssetResponse:
    if kind not in ALLOWED_KINDS:
        raise HTTPException(status_code=422, detail=f"kind must be one of {sorted(ALLOWED_KINDS)}")
    data = await file.read()
    if not data:
        raise HTTPException(status_code=422, detail="empty file")
    ext = os.path.splitext(file.filename or "")[1].lower() or ".bin"
    key = f"library/{uuid.uuid4().hex}{ext}"
    LocalStorage(get_settings().storage_dir).put(key, data)
    asset = await create_media_asset(
        session,
        kind=kind,
        title=(title.strip() or (file.filename or "Upload")),
        url="",
        storage_key=key,
        tags=[t.strip() for t in tags.split(",") if t.strip()],
        source="upload",
    )
    return _to_response(request, asset)


@router.delete("/assets/{asset_id}", status_code=204)
async def remove_asset(
    asset_id: uuid.UUID, session: AsyncSession = Depends(get_session)
) -> None:
    if not await delete_media_asset(session, asset_id):
        raise HTTPException(status_code=404, detail="asset not found")
