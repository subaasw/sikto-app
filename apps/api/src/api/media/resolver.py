"""Resolve an asset query to a concrete, themeable image URL for a scene.

Tries the user's media library first (uploads win, so users can override the
look), then free online providers (Iconify icons, recolored to the palette).
Best-effort: returns None when nothing fits so the caller degrades gracefully —
a scene without a confident asset simply stays text-only.
"""

import logging
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from api.media.providers import search_icons, search_illustrations
from api.media.repository import search_media_assets

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
) -> ResolvedAsset | None:
    """Resolve a query to an image. Prefers professional full-color illustrations,
    falls back to a recolored mono icon. A `registry` (passed across a lesson)
    makes the same concept always resolve to the same asset → consistent, reusable
    art, no odd mixing within a video."""
    keywords = _keywords(query)
    if not keywords:
        return None
    key = " ".join(keywords)
    if registry is not None and key in registry:
        return registry[key]

    result = await _lookup(session, keywords, color)
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


async def _first_relevant(search, term: str, keywords: list[str]):
    try:
        results = await search(term, 6)
    except Exception:
        logger.warning("asset search failed for %r", term, exc_info=True)
        return None
    return next((r for r in results if _relevant(r.title, keywords)), None)


async def _lookup(
    session: AsyncSession | None, keywords: list[str], color: str | None
) -> ResolvedAsset | None:
    # 1) User uploads / imported library assets win.
    if session is not None:
        uploads = await search_media_assets(session, tags=keywords, kind=None, limit=1)
        for asset in uploads:
            if asset.url:
                return ResolvedAsset(url=asset.url, kind="upload", source="library")

    # Iconify search returns nothing for multi-word phrases ("leaf with sunlight"
    # -> []), so try the two-word phrase first, then single keywords MOST-SPECIFIC
    # first (longer words are more depictable).
    by_specificity = sorted(keywords, key=len, reverse=True)
    terms = list(dict.fromkeys([" ".join(keywords[:2]), *by_specificity]))

    # 2) Professional full-color illustration (validated relevance; not recolored).
    for term in terms:
        hit = await _first_relevant(search_illustrations, term, keywords)
        if hit is not None:
            return ResolvedAsset(url=hit.url, kind="illustration", source="iconify-color")

    # 3) Fallback: a mono Iconify icon, recolored to the palette.
    for term in terms:
        hit = await _first_relevant(search_icons, term, keywords)
        if hit is not None:
            return ResolvedAsset(url=_recolor_icon(hit.url, color), kind="icon", source="iconify")

    return None
