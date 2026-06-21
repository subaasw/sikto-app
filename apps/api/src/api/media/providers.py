"""Free, key-less online media providers: search the web for icons and images
that can be imported into the media library.

- Icons: Iconify (https://iconify.design) — huge, free, no key.
- Images: Openverse (https://openverse.org) — CC-licensed, no key.

Everything is best-effort: a network failure returns an empty list rather than
breaking the request.
"""

import logging
from dataclasses import dataclass, field

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


async def _get_json(url: str, params: dict[str, object]) -> dict | None:
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT, headers={"User-Agent": _UA}) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            return resp.json()
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


async def search_online(query: str, kind: str, k: int = 16) -> list[MediaResult]:
    """Dispatch to the right provider for the requested kind."""
    query = query.strip()
    if not query:
        return []
    if kind == "icon":
        return await search_icons(query, k)
    return await search_images(query, k)
