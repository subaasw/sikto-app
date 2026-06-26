"""Art direction: turn plain text slides into asset-backed archetypes.

Two layers:

- An **LLM art-director** (when an ``llm`` is supplied) looks at every plain slide
  and picks the layout that best communicates it — a talking presenter, a hero
  image, an icon grid, a bold poster, or plain text — plus a concrete visual to
  illustrate it. One batched call per lesson.
- A **rule-based fallback** runs whenever the LLM is absent or its choice can't be
  realised (e.g. no image resolves). It's the original heuristic director, so the
  pipeline degrades gracefully and stays testable without a model.

Best-effort throughout: any failure leaves a scene as plain text rather than
breaking the lesson.
"""

import logging
from typing import TYPE_CHECKING

from sqlalchemy.ext.asyncio import AsyncSession

from api.media.resolver import ResolvedAsset, resolve_asset
from api.scenes.assemble import (
    hero_layout,
    icon_grid_layout,
    poster_layout,
    poster_text_layout,
    presenter_layout,
)
from api.scenes.schema import ArtDirection, ElementType, Scene, SceneArt, SceneDocument, SceneKind
from api.scenes.templates import Template

if TYPE_CHECKING:
    from api.agent_engine.llm import StructuredLLM

logger = logging.getLogger("api.art")

_MAX_WORDS_FOR_GRID = 5

ARCHETYPE_SYSTEM = (
    "You are Sikto's art director. For each plain text slide, choose the layout that best "
    "communicates it, and name a concrete visual subject to illustrate it. Layouts:\n"
    "- presenter: a friendly talking figure delivering the point (great for an intro, a "
    "transition, or a conclusion).\n"
    "- hero: a heading with a few bullets beside one feature image (great for an explained "
    "concept with supporting points).\n"
    "- icon_grid: 2-4 short parallel points, each shown as its own icon (great for a list of "
    "features, pillars, or steps).\n"
    "- poster: one dominant image with a single headline and minimal text (great for a bold, "
    "visual, high-impact beat).\n"
    "- plain: keep it as text only (when no image would genuinely help).\n"
    "Give a 2-4 word visual_query naming a depictable subject (a real object or scene), or null "
    "for plain. Reference each slide by its id. Vary the layouts so the lesson isn't monotonous."
)


def _bullet_texts(scene: Scene) -> list[str]:
    return [e.items[0] for e in scene.elements if e.type == ElementType.bullets and e.items]


def _heading_of(scene: Scene) -> str | None:
    el = next((e for e in scene.elements if e.type == ElementType.heading and e.text), None)
    return el.text if el else None


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


def _emphasis_of(scene: Scene) -> list[str] | None:
    el = next((e for e in scene.elements if e.type == ElementType.heading), None)
    return el.emphasis if el else None


async def _make_poster(
    session: AsyncSession | None,
    scene: Scene,
    color: str | None,
    registry: dict[str, ResolvedAsset] | None,
    query: str | None = None,
) -> Scene:
    """A plain slide becomes a visual-first poster — one dominant image + a single
    headline (no bullets). Falls back to a bold typographic poster when no image
    resolves, so a poster choice never shows a bulleted text slide."""
    heading = _heading_of(scene)
    if not heading:
        return scene
    # Query the concrete visual subject, never the (often metaphorical) headline.
    vq = query or scene.visual_query
    asset = (
        await resolve_asset(session, vq, color=color, registry=registry, prefer_photo=True)
        if vq
        else None
    )
    n = scene.narration
    if asset is not None:
        return poster_layout(
            scene.id, heading, asset.url,
            narration=n.text, caption=n.caption, delivery=n.delivery, emphasis=_emphasis_of(scene),
        )
    return poster_text_layout(
        scene.id, heading, narration=n.text, caption=n.caption, delivery=n.delivery,
        emphasis=_emphasis_of(scene),
    )


def _make_presenter(scene: Scene) -> Scene:
    """Turn a plain slide into a talking stick-figure presenter. Procedural — no
    asset lookup, so it always succeeds (the figure lip-syncs the narration)."""
    return presenter_layout(
        scene.id,
        _heading_of(scene) or "",
        _bullet_texts(scene)[:2],
        narration=scene.narration.text,
        emotion=scene.narration.delivery,
        caption=scene.narration.caption,
        delivery=scene.narration.delivery,
        emphasis=_emphasis_of(scene),
    )


async def _make_hero(
    session: AsyncSession | None,
    scene: Scene,
    color: str | None,
    registry: dict[str, ResolvedAsset] | None,
    query: str | None = None,
) -> Scene | None:
    """Heading + bullets beside one feature image. None when no image resolves."""
    heading = _heading_of(scene)
    if not heading:
        return None
    asset = await resolve_asset(session, query or scene.visual_query or heading, color=color, registry=registry)
    if asset is None:
        return None
    n = scene.narration
    return hero_layout(
        scene.id, heading, _bullet_texts(scene), asset.url,
        narration=n.text, caption=n.caption, delivery=n.delivery, emphasis=_emphasis_of(scene),
    )


async def _make_icon_grid(
    session: AsyncSession | None,
    scene: Scene,
    color: str | None,
    registry: dict[str, ResolvedAsset] | None,
) -> Scene | None:
    """A short, parallel bullet list becomes an icon-per-point grid. None unless
    EVERY point resolves to an icon (no half-empty grids)."""
    heading = _heading_of(scene)
    bullets = _bullet_texts(scene)
    if not heading or not (2 <= len(bullets) <= 4):
        return None
    if not all(len(t.split()) <= _MAX_WORDS_FOR_GRID for t in bullets):
        return None
    resolved = [(t, await resolve_asset(session, t, color=color, registry=registry)) for t in bullets]
    if not all(asset is not None for _, asset in resolved):
        return None
    n = scene.narration
    return icon_grid_layout(
        scene.id, heading, [(t, a.url) for t, a in resolved],  # type: ignore[union-attr]
        narration=n.text, caption=n.caption, delivery=n.delivery, emphasis=_emphasis_of(scene),
    )


async def _upgrade(
    session: AsyncSession | None,
    scene: Scene,
    color: str | None,
    registry: dict[str, ResolvedAsset] | None = None,
) -> Scene | None:
    """Rule-based fallback for a plain slide: icon-grid a short parallel list,
    otherwise a hero image. Returns None when nothing resolves."""
    if not _is_plain_slide(scene):
        return None
    grid = await _make_icon_grid(session, scene, color, registry)
    if grid is not None:
        return grid
    return await _make_hero(session, scene, color, registry)


async def _plan_art(
    llm: "StructuredLLM",
    doc: SceneDocument,
    plain_ids: list[int],
    is_marketing: bool,
) -> dict[str, SceneArt]:
    """One batched call: ask the LLM to pick a layout + visual for each plain slide.
    Best-effort — failure returns {} so the rule-based director takes over."""
    if not plain_ids:
        return {}
    blocks = []
    for i in plain_ids:
        s = doc.scenes[i]
        blocks.append(
            f"[{s.id}] heading: {_heading_of(s) or ''}\n"
            f"  points: {_bullet_texts(s)}\n"
            f"  narration: {s.narration.text}"
        )
    prompt = "Plain slides to art-direct:\n\n" + "\n\n".join(blocks)
    if is_marketing:
        prompt += (
            "\n\nThis is a MARKETING video: strongly prefer 'poster' (one bold visual + a single "
            "headline) and never use 'presenter'."
        )
    try:
        plan = await llm.generate(ARCHETYPE_SYSTEM, prompt, ArtDirection)
    except Exception:
        logger.warning("art-director planning failed; using rules", exc_info=True)
        return {}
    return {a.scene_id: a for a in plan.scenes}


async def _apply_archetype(
    session: AsyncSession | None,
    scene: Scene,
    art: SceneArt,
    color: str | None,
    registry: dict[str, ResolvedAsset] | None,
) -> Scene | None:
    """Realise an explicit LLM layout choice. None → couldn't (caller falls back)."""
    if art.archetype == "presenter":
        return _make_presenter(scene)
    if art.archetype == "poster":
        return await _make_poster(session, scene, color, registry, art.visual_query)
    if art.archetype == "hero":
        return await _make_hero(session, scene, color, registry, art.visual_query)
    if art.archetype == "icon_grid":
        return await _make_icon_grid(session, scene, color, registry)
    if art.archetype == "plain":
        return scene  # keep text-only, deliberately
    return None  # "auto" → fall through to rules


async def art_direct(
    session: AsyncSession | None,
    doc: SceneDocument,
    template: Template,
    llm: "StructuredLLM | None" = None,
) -> SceneDocument:
    """Art-direct the lesson. With an ``llm``, an art-director agent chooses each
    plain slide's layout; without one (or when a choice can't be realised), the
    rule-based director runs: bookend the lesson with a talking presenter and
    upgrade other eligible slides with a resolved graphic. Diagrams, equations,
    and stat scenes are never touched. Marketing is visual-first (no presenter)."""
    color = template.theme.primary
    is_marketing = template.id == "marketing"
    plain = [i for i, s in enumerate(doc.scenes) if _is_plain_slide(s)]

    # Rule-based presenter placement (fallback): first plain slide (intro) and, for
    # longer lessons, the last (conclusion). Marketing skips the talking presenter.
    presenter_at: set[int] = set()
    if plain and not is_marketing:
        presenter_at.add(plain[0])
        if len(plain) > 2:
            presenter_at.add(plain[-1])

    plan = await _plan_art(llm, doc, plain, is_marketing) if llm is not None else {}
    registry: dict[str, ResolvedAsset] = {}  # concept → asset, reused for consistent art
    scenes: list[Scene] = []
    for i, scene in enumerate(doc.scenes):
        try:
            directed: Scene | None = None
            art = plan.get(scene.id)
            if art is not None and art.archetype != "auto":
                directed = await _apply_archetype(session, scene, art, color, registry)
            if directed is None:  # no plan, or the explicit choice couldn't be realised
                if is_marketing and _is_plain_slide(scene):
                    directed = await _make_poster(session, scene, color, registry)
                elif i in presenter_at:
                    directed = _make_presenter(scene)
                else:
                    directed = await _upgrade(session, scene, color, registry)
        except Exception:
            logger.warning("art-direction failed for scene %s", scene.id, exc_info=True)
            directed = None
        scenes.append(directed or scene)
    return doc.model_copy(update={"scenes": scenes})
