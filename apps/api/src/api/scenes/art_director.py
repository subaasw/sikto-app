"""Rule-based art direction: upgrade plain text slides into asset-backed
archetypes by resolving a relevant graphic.

A first cut — the LLM art-director (picking from the full archetype catalog)
comes later; this already gets real imagery onto scenes end-to-end. Best-effort:
a scene without a confident asset, or any failure, leaves the scene untouched.
"""

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from api.media.resolver import ResolvedAsset, resolve_asset
from api.scenes.assemble import (
    hero_layout,
    icon_grid_layout,
    poster_layout,
    poster_text_layout,
    presenter_layout,
)
from api.scenes.schema import ElementType, Scene, SceneDocument, SceneKind
from api.scenes.templates import Template

logger = logging.getLogger("api.art")

_MAX_WORDS_FOR_GRID = 5


def _bullet_texts(scene: Scene) -> list[str]:
    return [e.items[0] for e in scene.elements if e.type == ElementType.bullets and e.items]


def _is_plain_slide(scene: Scene) -> bool:
    """A text slide (heading + optional bullets) — not a diagram/equation/image."""
    if scene.kind != SceneKind.slide:
        return False
    if any(
        e.type in (ElementType.card, ElementType.shape, ElementType.latex, ElementType.image)
        for e in scene.elements
    ):
        return False
    return any(e.type == ElementType.heading and e.text for e in scene.elements)


async def _make_poster(
    session: AsyncSession | None,
    scene: Scene,
    color: str | None,
    registry: dict[str, ResolvedAsset] | None = None,
) -> Scene:
    """Marketing: a plain slide becomes a visual-first poster — one dominant image
    + a single headline (no bullets). Falls back to a bold typographic poster when
    no image resolves, so marketing never shows a bulleted text slide."""
    heading = next((e for e in scene.elements if e.type == ElementType.heading and e.text), None)
    if heading is None or not heading.text:
        return scene
    # Query ONLY the LLM's concrete visual subject, never the headline — marketing
    # headlines are metaphorical ("Ship faster" must not resolve to a boat).
    asset = (
        await resolve_asset(session, scene.visual_query, color=color, registry=registry, prefer_photo=True)
        if scene.visual_query
        else None
    )
    n = scene.narration
    if asset is not None:
        return poster_layout(
            scene.id, heading.text, asset.url,
            narration=n.text, caption=n.caption, delivery=n.delivery, emphasis=heading.emphasis,
        )
    return poster_text_layout(
        scene.id, heading.text,
        narration=n.text, caption=n.caption, delivery=n.delivery, emphasis=heading.emphasis,
    )


def _make_presenter(scene: Scene) -> Scene:
    """Turn a plain slide into a talking stick-figure presenter. Procedural — no
    asset lookup, so it always succeeds (the figure lip-syncs the narration)."""
    heading = next(e for e in scene.elements if e.type == ElementType.heading)
    return presenter_layout(
        scene.id,
        heading.text or "",
        _bullet_texts(scene)[:2],
        narration=scene.narration.text,
        emotion=scene.narration.delivery,
        caption=scene.narration.caption,
        delivery=scene.narration.delivery,
        emphasis=heading.emphasis,
    )


async def _upgrade(
    session: AsyncSession | None,
    scene: Scene,
    color: str | None,
    registry: dict[str, ResolvedAsset] | None = None,
) -> Scene | None:
    if scene.kind != SceneKind.slide:
        return None
    # Leave diagrams (cards/connectors), equations, and already-illustrated
    # scenes alone — only plain text slides get art-directed.
    if any(
        e.type in (ElementType.card, ElementType.shape, ElementType.latex, ElementType.image)
        for e in scene.elements
    ):
        return None
    heading = next((e for e in scene.elements if e.type == ElementType.heading), None)
    if heading is None or not heading.text:
        return None

    bullets = _bullet_texts(scene)

    # icon_grid: a short bullet list becomes an icon-per-point grid — but only if
    # every point resolves to an icon (no half-empty grids).
    if 2 <= len(bullets) <= 4 and all(len(t.split()) <= _MAX_WORDS_FOR_GRID for t in bullets):
        resolved = [(t, await resolve_asset(session, t, color=color, registry=registry)) for t in bullets]
        if all(asset is not None for _, asset in resolved):
            return icon_grid_layout(
                scene.id,
                heading.text,
                [(t, asset.url) for t, asset in resolved],  # type: ignore[union-attr]
                narration=scene.narration.text,
                caption=scene.narration.caption,
                delivery=scene.narration.delivery,
                emphasis=heading.emphasis,
            )

    # hero: a single feature image beside the text. Content-driven — use the
    # LLM's visual hint when present, otherwise derive from the heading, so every
    # plain slide gets a relevant graphic (not just the ones the model tagged).
    query = scene.visual_query or heading.text
    asset = await resolve_asset(session, query, color=color, registry=registry)
    if asset is not None:
        return hero_layout(
            scene.id,
            heading.text,
            bullets,
            asset.url,
            narration=scene.narration.text,
            caption=scene.narration.caption,
            delivery=scene.narration.delivery,
            emphasis=heading.emphasis,
        )
    return None


async def art_direct(
    session: AsyncSession, doc: SceneDocument, template: Template
) -> SceneDocument:
    """Walk the lesson: bookend it with a talking presenter (intro + conclusion),
    and upgrade the other eligible slides with a resolved graphic. Diagrams,
    equations, and stat scenes are never presenter-led."""
    color = template.theme.primary
    is_marketing = template.id == "marketing"
    # Content-aware placement: the first plain slide (intro) and, for longer
    # lessons, the last plain slide (conclusion) get the presenter. Marketing is
    # visual-first, so it skips the talking presenter entirely.
    plain = [i for i, s in enumerate(doc.scenes) if _is_plain_slide(s)]
    presenter_at: set[int] = set()
    if plain and not is_marketing:
        presenter_at.add(plain[0])
        if len(plain) > 2:
            presenter_at.add(plain[-1])

    registry: dict[str, ResolvedAsset] = {}  # concept → resolved asset, reused across the lesson
    scenes: list[Scene] = []
    for i, scene in enumerate(doc.scenes):
        try:
            if is_marketing and _is_plain_slide(scene):
                scenes.append(await _make_poster(session, scene, color, registry))
                continue
            if i in presenter_at:
                scenes.append(_make_presenter(scene))
                continue
            upgraded = await _upgrade(session, scene, color, registry)
        except Exception:
            logger.warning("art-direction failed for scene %s", scene.id, exc_info=True)
            upgraded = None
        scenes.append(upgraded or scene)
    return doc.model_copy(update={"scenes": scenes})
