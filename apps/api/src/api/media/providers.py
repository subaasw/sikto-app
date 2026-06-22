"""Free, key-less online media providers: search the web for icons and images
that can be imported into the media library.

- Icons: Iconify (https://iconify.design) — huge, free, no key.
- Images: Openverse (https://openverse.org) — CC-licensed, no key.

Everything is best-effort: a network failure returns an empty list rather than
breaking the request.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any

import httpx

logger = logging.getLogger("api.media.providers")

_TIMEOUT = 12.0
_UA = "sikto-media/0.1 (+https://github.com/sikto)"


@dataclass
class MediaResult:
    title: str
    url: str
    thumbnail: str
    source: str
    kind: str
    license: str | None = None
    tags: list[str] = field(default_factory=list)


async def _get_json(url: str, params: dict[str, str | int]) -> dict[str, Any] | None:
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT, headers={"User-Agent": _UA}) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            data: Any = resp.json()
            return data if isinstance(data, dict) else None
    except Exception:
        logger.warning("media provider request failed: %s", url, exc_info=True)
        return None


async def search_icons(query: str, k: int) -> list[MediaResult]:
    data = await _get_json("https://api.iconify.design/search", {"query": query, "limit": k})
    if not data:
        return []
    out: list[MediaResult] = []
    for ref in data.get("icons", [])[:k]:
        prefix, _, name = str(ref).partition(":")
        if not name:
            continue
        svg = f"https://api.iconify.design/{prefix}/{name}.svg"
        out.append(
            MediaResult(
                title=name.replace("-", " "),
                url=svg,
                thumbnail=svg,
                source="iconify",
                kind="icon",
                license="open source",
                tags=[query, *name.split("-")],
            )
        )
    return out


# Iconify-hosted, full-COLOR illustration sets — professional, multicolor
# graphics (not flat monochrome icons). Reliably served by Iconify, so no
# vendoring/dead-CDN risk. These are NOT recolored (they carry their own palette).
_ILLUSTRATION_SETS = "fluent-emoji-flat,noto,flat-color-icons,streamline-color"


async def search_illustrations(query: str, k: int) -> list[MediaResult]:
    data = await _get_json(
        "https://api.iconify.design/search",
        {"query": query, "limit": k, "prefixes": _ILLUSTRATION_SETS},
    )
    if not data:
        return []
    out: list[MediaResult] = []
    for ref in data.get("icons", [])[:k]:
        prefix, _, name = str(ref).partition(":")
        if not name:
            continue
        svg = f"https://api.iconify.design/{prefix}/{name}.svg"
        out.append(
            MediaResult(
                title=name.replace("-", " "),
                url=svg,
                thumbnail=svg,
                source="iconify-color",
                kind="illustration",
                license="open source",
                tags=[query, *name.split("-")],
            )
        )
    return out


async def search_images(query: str, k: int) -> list[MediaResult]:
    data = await _get_json(
        "https://api.openverse.org/v1/images/", {"q": query, "page_size": k}
    )
    if not data:
        return []
    out: list[MediaResult] = []
    for row in data.get("results", [])[:k]:
        url = row.get("url")
        if not url:
            continue
        out.append(
            MediaResult(
                title=str(row.get("title") or query)[:120],
                url=url,
                thumbnail=row.get("thumbnail") or url,
                source="openverse",
                kind="image",
                license=row.get("license"),
                tags=[query],
            )
        )
    return out


# thesvg.org — software/brand logos (OpenAI, GitHub, Stripe…). A static manifest
# fetched ONCE (cached) from the jsDelivr CDN mirror; SVGs served from the same CDN.
_THESVG_MANIFEST = "https://cdn.jsdelivr.net/gh/glincker/thesvg@main/src/data/icons.json"
_THESVG_SVG = "https://cdn.jsdelivr.net/gh/glincker/thesvg@main/public/icons/{slug}/{variant}.svg"

_brand_icons: list[dict[str, Any]] | None = None
_brand_lock = asyncio.Lock()


async def _brand_manifest() -> list[dict[str, Any]]:
    global _brand_icons
    if _brand_icons is not None:
        return _brand_icons
    async with _brand_lock:
        if _brand_icons is None:
            try:
                async with httpx.AsyncClient(timeout=_TIMEOUT, headers={"User-Agent": _UA}) as client:
                    resp = await client.get(_THESVG_MANIFEST)
                    resp.raise_for_status()
                    data = resp.json()
            except Exception:
                logger.warning("thesvg manifest fetch failed", exc_info=True)
                return []  # don't cache the failure — retry on the next search
            icons = data.get("icons") if isinstance(data, dict) else data
            _brand_icons = icons if isinstance(icons, list) else []
    return _brand_icons


def _brand_variant(icon: dict[str, Any]) -> str:
    variants = icon.get("variants") or icon.get("variant")
    if isinstance(variants, dict) and variants:
        return "default" if "default" in variants else next(iter(variants))
    if isinstance(variants, list) and variants:
        return "default" if "default" in variants else str(variants[0])
    return "default"


async def search_brand_icons(query: str, k: int) -> list[MediaResult]:
    """Software/brand logos from thesvg.org, matched client-side on slug/title/alias."""
    q = query.lower().strip()
    if not q:
        return []
    out: list[MediaResult] = []
    for icon in await _brand_manifest():
        slug = str(icon.get("slug") or "")
        if not slug:
            continue
        title = str(icon.get("title") or slug)
        aliases = icon.get("aliases") or []
        hay = " ".join([slug, title, *(str(a) for a in aliases)]).lower()
        if q in hay:
            url = _THESVG_SVG.format(slug=slug, variant=_brand_variant(icon))
            out.append(
                MediaResult(
                    title=title, url=url, thumbnail=url, source="thesvg", kind="logo",
                    license=icon.get("license"), tags=[query, slug],
                )
            )
            if len(out) >= k:
                break
    return out


async def search_online(query: str, kind: str, k: int = 16) -> list[MediaResult]:
    """Dispatch to the right provider for the requested kind."""
    query = query.strip()
    if not query:
        return []
    if kind == "icon":
        return await search_icons(query, k)
    if kind == "logo":
        return await search_brand_icons(query, k)
    if kind == "background":
        return await search_images(f"{query} abstract background", k)
    return await search_images(query, k)
