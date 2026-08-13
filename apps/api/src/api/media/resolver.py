"""Resolve an asset query to a concrete, themeable image URL for a scene.

Tries the user's media library first (uploads win, so users can override the
look), then free online providers (Iconify icons, recolored to the palette).
Best-effort: returns None when nothing fits so the caller degrades gracefully —
a scene without a confident asset simply stays text-only.
"""

import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from api.config import get_settings
from api.media.providers import MediaResult, search_icons, search_illustrations, search_images
from api.media.repository import cache_resolved_asset, search_media_assets
from api.media.svg import recolor_svg, svg_data_uri
from api.models import MediaAsset
from api.storage import LocalStorage

logger = logging.getLogger("api.media.resolver")

# Tiny stop-word list so a heading like "How the brain learns" yields useful
# query keywords ("brain", "learns") rather than noise.
_STOP = {
    "the", "a", "an", "of", "to", "and", "or", "in", "on", "for", "is", "are",
    "with", "how", "why", "what", "your", "you", "this", "that", "it", "as", "by",
}


@dataclass
class ResolvedAsset:
    url: str
    kind: str  # "upload" | "icon"
    source: str


def _keywords(text: str, k: int = 4) -> list[str]:
    words = [w.strip(".,:;!?()[]\"'").lower() for w in (text or "").split()]
    return [w for w in words if len(w) > 2 and w not in _STOP][:k]


def _recolor_icon(url: str, color: str | None) -> str:
    """Iconify serves monochrome SVGs; `?color=` tints them to the theme."""
    if not color:
        return url
    return f"{url}?color={color.replace('#', '%23')}"


async def resolve_asset(
    session: AsyncSession | None,
    query: str,
    *,
    color: str | None = None,
    registry: dict[str, "ResolvedAsset"] | None = None,
    prefer_photo: bool = False,
    allow_icon: bool = True,
) -> ResolvedAsset | None:
    """Resolve a query to an image. By default prefers full-color illustrations,
    falling back to a recolored mono icon (unless ``allow_icon`` is False — see
    ``_lookup``). With ``prefer_photo`` (marketing) it
    resolves a real photo (Openverse) first — a dominant photo reads far better
    than an icon. A `registry` (passed across a lesson) makes the same concept
    always resolve to the same asset → consistent art, no odd mixing."""
    keywords = _keywords(query)
    if not keywords:
        return None
    key = ("photo:" if prefer_photo else "") + " ".join(keywords)
    if registry is not None and key in registry:
        return registry[key]

    result = await _lookup(session, keywords, color, prefer_photo, allow_icon)
    if registry is not None and result is not None:
        registry[key] = result
    return result


def _relevant(title: str, keywords: list[str]) -> bool:
    """A result is relevant only if its name shares a word-stem with the query —
    so a "wifi-router" is rejected for "planets" but "earth-1" passes for "earth"
    (and "planet" passes for "planets"). No match → we'd rather show no image than
    a wrong one."""
    tokens = title.lower().replace("-", " ").split()
    for kw in keywords:
        if len(kw) < 4:
            continue
        for tok in tokens:
            # Equal or shared 4+ char prefix (planet/planets, earth/earth-1) —
            # but NOT mere substrings ("outer" must not match "router").
            if len(tok) >= 4 and (tok == kw or kw.startswith(tok[:4]) or tok.startswith(kw[:4])):
                return True
    return False


async def _first_relevant(
    search: Callable[[str, int], Awaitable[list[MediaResult]]],
    term: str,
    keywords: list[str],
) -> MediaResult | None:
    try:
        results = await search(term, 6)
    except Exception:
        logger.warning("asset search failed for %r", term, exc_info=True)
        return None
    return next((r for r in results if _relevant(r.title, keywords)), None)


def _resolve_upload(asset: MediaAsset, color: str | None) -> "ResolvedAsset | None":
    """A library asset → a usable image URL. Imported assets carry an external
    url. Uploaded files live in storage as `storage_key`; SVG uploads are inlined
    as a data URI (recolored to the palette when they're icons) so they stay
    editable yet themeable. Non-SVG uploads aren't resolvable here yet."""
    if asset.url:
        return ResolvedAsset(url=asset.url, kind="upload", source="library")
    key = asset.storage_key
    if not key or not key.lower().endswith(".svg"):
        return None  # ponytail: raster uploads need base_url to serve; out of scope here
    try:
        svg = LocalStorage(get_settings().storage_dir).get(key).decode()
    except Exception:
        logger.warning("could not read uploaded svg %r", key, exc_info=True)
        return None
    if color and asset.kind == "icon":
        svg = recolor_svg(svg, color)
    return ResolvedAsset(url=svg_data_uri(svg), kind="upload", source="library")


async def _cache(
    session: AsyncSession | None, kind: str, hit: MediaResult, keywords: list[str], source: str
) -> None:
    """Best-effort persist of a resolved full-colour asset into the library so later
    lessons reuse the same vetted art. Only illustrations/photos are cached — mono
    icons are theme-recolored at use-time, so a baked-in colour URL would be wrong
    under a different theme (and icons are the fallback, not the default)."""
    if session is None:
        return
    try:
        await cache_resolved_asset(session, kind=kind, title=hit.title, url=hit.url, tags=keywords, source=source)
    except Exception:
        logger.warning("could not cache resolved asset %r", hit.url, exc_info=True)


async def _lookup(
    session: AsyncSession | None,
    keywords: list[str],
    color: str | None,
    prefer_photo: bool = False,
    allow_icon: bool = True,
) -> ResolvedAsset | None:
    # 1) User uploads / imported library assets win.
    if session is not None:
        uploads = await search_media_assets(session, tags=keywords, kind=None, limit=1)
        for asset in uploads:
            resolved = _resolve_upload(asset, color)
            if resolved is not None:
                return resolved

    # Iconify search returns nothing for multi-word phrases ("leaf with sunlight"
    # -> []), so try the two-word phrase first, then single keywords MOST-SPECIFIC
    # first (longer words are more depictable).
    by_specificity = sorted(keywords, key=len, reverse=True)
    terms = list(dict.fromkeys([" ".join(keywords[:2]), *by_specificity]))

    # 2) Marketing: a real photo of the concept (Openverse, keyless). Openverse
    # free-text search is noisy, so apply the SAME word-stem relevance check used
    # for icons against the photo title — an unrelated top hit is worse than no
    # photo (the caller then falls back to a clean typographic poster).
    if prefer_photo:
        for term in terms:
            hit = await _first_relevant(search_images, term, keywords)
            if hit is not None:
                await _cache(session, "image", hit, keywords, "openverse")
                return ResolvedAsset(url=hit.url, kind="photo", source="openverse")

    # 3) Professional full-color illustration (validated relevance; not recolored).
    for term in terms:
        hit = await _first_relevant(search_illustrations, term, keywords)
        if hit is not None:
            await _cache(session, "illustration", hit, keywords, "iconify-color")
            return ResolvedAsset(url=hit.url, kind="illustration", source="iconify-color")

    # 4) Fallback: a mono Iconify icon, recolored. Skipped for marketing — a tiny
    # mono icon shown full-bleed is exactly the "irrelevant" look we're avoiding.
    # Also gated on `allow_icon`: an Iconify name can literally contain a query word
    # in the WRONG sense ("French Revolution" -> french-fries, "binary search" ->
    # magnifier), which no word-stem check can catch. So we only fall back to a mono
    # icon when the brain explicitly asked for one (visual_kind == "icon", a clean
    # symbol); for richer/abstract subjects we'd rather stay text-only.
    if not prefer_photo and allow_icon:
        for term in terms:
            hit = await _first_relevant(search_icons, term, keywords)
            if hit is not None:
                return ResolvedAsset(url=_recolor_icon(hit.url, color), kind="icon", source="iconify")

    return None
