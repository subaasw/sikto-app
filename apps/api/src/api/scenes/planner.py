"""Compose each slide scene as semantic layers (LLM), resolve image layers to
assets, and solve their layout. Replaces the archetype art-director.

Best-effort: any failure (no LLM, bad response, asset miss) falls back to a
deterministic composition, so the lesson never breaks.
"""

import logging
import re

from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from api.agent_engine.llm import StructuredLLM
from api.media.resolver import resolve_asset
from api.scenes.layout import solve_layout
from api.scenes.schema import (
    ElementType,
    Layer,
    LayerKind,
    LayerMotion,
    LayerSize,
    Region,
    Scene,
    SceneDocument,
    SceneKind,
    SceneTheme,
    VoiceEnergy,
    VoiceProfile,
)
from api.voices import Tone, voice_for

logger = logging.getLogger("api.planner")

# --- creative direction: per-video look + narrator, chosen by the LLM ---------

_DIRECTION_SYSTEM = (
    "You are the creative director for a short explainer rendered on a WHITEBOARD. "
    "From the lesson's title and summary, choose a look and a narrator that fit the "
    "subject's mood. The board MUST stay a clean, LIGHT near-white (so dark marker "
    "text is readable) — pick a vivid ACCENT colour for highlights and the marker. "
    "Choose a font and a narrator tone + spoken energy. Match the subject: a fun or "
    "consumer topic -> playful/energetic; a serious or technical topic -> "
    "authoritative and balanced. Keep it tasteful, professional, and easy to follow."
)

_SAFE_FONTS = {"Geist", "Inter", "Poppins", "Fraunces", "Space Grotesk"}
_HEX = re.compile(r"^#[0-9a-fA-F]{6}$")


class _CreativeDirection(BaseModel):
    primary: str = Field("#2563eb", description="Vivid accent hex like '#e11d48' for highlights/marker.")
    background: str = Field("#f6f7f9", description="A LIGHT near-white board hex (must stay light for readable text).")
    font: str = Field("Geist", description="Geist, Inter, Poppins, Fraunces, or Space Grotesk.")
    tone: Tone = Field("warm", description="Narrator: warm, playful, energetic, or authoritative.")
    energy: VoiceEnergy = Field("balanced", description="Spoken energy: calm, balanced, energetic, or hype.")


def _safe_hex(value: str, fallback: str) -> str:
    v = (value or "").strip()
    return v if _HEX.match(v) else fallback


def _light_or(hex6: str, fallback: str) -> str:
    """Keep a colour only if it's light enough for dark text to read on."""
    r, g, b = (int(hex6[i : i + 2], 16) / 255 for i in (1, 3, 5))
    return hex6 if (0.2126 * r + 0.7152 * g + 0.0722 * b) >= 0.7 else fallback


async def direct_creative(
    document: SceneDocument, *, llm: StructuredLLM | None, gender: str | None
) -> SceneDocument:
    """Set the video's theme + narrator voice from its topic. Best-effort: a clean
    light theme + the user's gender voice when no/failed LLM (lesson never breaks)."""
    tone: str = "warm"
    energy: str = "balanced"
    if llm is not None:
        try:
            d = await llm.generate(
                _DIRECTION_SYSTEM, f"Title: {document.title}\nSummary: {document.summary}", _CreativeDirection
            )
            document.theme = SceneTheme(
                primary=_safe_hex(d.primary, "#2563eb"),
                background=_light_or(_safe_hex(d.background, "#f6f7f9"), "#f6f7f9"),
                foreground="#1f2937",
                font=d.font if d.font in _SAFE_FONTS else "Geist",
            )
            tone, energy = d.tone, d.energy
        except Exception:
            logger.warning("creative direction failed for %r, using defaults", document.title, exc_info=True)
            document.theme = SceneTheme()
    else:
        document.theme = SceneTheme()
    document.voice = VoiceProfile(voice=voice_for(gender, tone), energy=energy)  # type: ignore[arg-type]
    return document

_SYSTEM = (
    "You compose one panel of a professional WHITEBOARD explainer as a stack of "
    "LAYERS that get drawn on, one at a time, by a hand with a marker. "
    "Use only these layer kinds: bg-texture (the board itself), image, headline, "
    "caption, sticker, shape. "
    "Place each with a semantic region (full-bleed, left, right, center, upper, lower, "
    "upper-third, lower-third) and a size (sm, md, lg, full). You do NOT control pixels "
    "— the system places each layer from its region/size, so think in composition, not "
    "coordinates. Always include exactly one bg-texture (full-bleed, the board) and one "
    "headline. Include at most one image layer; leave its content empty (the system fills "
    "the asset). Add a caption or a short sticker (a circled keyword) for the key idea. "
    "Keep it clean: 2-4 layers total. Caption/sticker content is short on-screen text, "
    "NOT the narration."
)


class _PlannedLayer(BaseModel):
    """What the LLM emits per layer — no `frame` (the solver owns pixels)."""

    kind: LayerKind
    content: str = Field("", description="text for headline/caption/sticker; leave empty for image/bg-texture")
    region: Region = "center"
    size: LayerSize = "md"
    depth: int = Field(1, description="parallax plane 0..2 (clamped if out of range)")
    motion: LayerMotion = "pop"


class _SceneLayers(BaseModel):
    layers: list[_PlannedLayer]


def _to_layers(planned: list[_PlannedLayer], image_src: str | None) -> list[Layer]:
    """Normalize the LLM's layers into solvable `Layer`s: fill the image asset,
    drop image layers with no asset, and guarantee a bg-texture + a headline."""
    out: list[Layer] = []
    for p in planned[:5]:  # cap so a runaway response can't crowd the stage
        content = image_src if p.kind == "image" else (p.content or None)
        if p.kind == "image" and not content:
            continue  # no asset resolved → let texture + type carry the scene
        out.append(
            Layer(
                kind=p.kind,
                content=content,
                region=p.region,
                size=p.size,
                depth=max(0, min(2, p.depth)),
                motion=p.motion,
            )
        )
    if not any(l.kind == "bg-texture" for l in out):
        out.insert(0, Layer(kind="bg-texture", region="full-bleed", size="full", depth=0, motion="none"))
    if not any(l.kind == "headline" for l in out):
        return []  # no headline → caller falls back to the deterministic composition
    return out


def scene_content(scene: Scene) -> dict:
    """Pull the text content the planner composes from a slide scene's elements."""
    heading = next(
        (e.text for e in scene.elements if e.type == ElementType.heading and e.text), ""
    )
    bullets: list[str] = []
    body = ""
    latex = ""
    for e in scene.elements:
        if e.type == ElementType.bullets and e.items:
            bullets.extend(e.items)
        elif e.type == ElementType.text and e.text and not body:
            body = e.text
        elif e.type == ElementType.latex and e.latex:
            latex = e.latex
    return {
        "heading": heading,
        "bullets": bullets,
        "body": body,
        "latex": latex,
        "visual": scene.visual_query or "",
    }


def fallback_layers(content: dict, image_src: str | None) -> list[Layer]:
    """Deterministic composition: textured bg + headline + optional cover image +
    one caption. Already solved (frames filled)."""
    layers = [
        Layer(kind="bg-texture", region="full-bleed", size="full", depth=0, motion="none"),
        Layer(
            kind="headline",
            content=content["heading"] or "",
            region="upper",
            size="lg",
            depth=2,
            motion="pop",
        ),
    ]
    if image_src:
        layers.append(
            Layer(kind="image", content=image_src, region="center", size="md", depth=1, motion="settle")
        )
    caption = content["bullets"][0] if content["bullets"] else content["body"]
    if caption:
        layers.append(
            Layer(kind="caption", content=caption, region="lower-third", size="sm", depth=2, motion="drift")
        )
    return solve_layout(layers)


def _content_prompt(content: dict) -> str:
    parts = [f"Heading: {content['heading']}"]
    if content["bullets"]:
        parts.append("Points: " + "; ".join(content["bullets"]))
    if content["body"]:
        parts.append(f"Body: {content['body']}")
    if content["visual"]:
        parts.append(f"Suggested visual: {content['visual']}")
    return "\n".join(parts)


async def _resolve_image_src(
    session: AsyncSession | None, visual: str, color: str | None, allow_icon: bool = True
) -> str | None:
    if not visual:
        return None
    try:
        asset = await resolve_asset(session, visual, color=color, allow_icon=allow_icon)
        return asset.url if asset else None
    except Exception:
        logger.warning("asset resolve failed for %r", visual, exc_info=True)
        return None


async def plan_layers(
    session: AsyncSession | None, document: SceneDocument, *, llm: StructuredLLM | None
) -> SceneDocument:
    """Compose layers for every slide scene; manim scenes pass through untouched."""
    color = document.theme.primary
    for scene in document.scenes:
        if scene.kind != SceneKind.slide:
            continue
        content = scene_content(scene)
        # Only let a slide fall back to a mono icon when the brain deliberately asked
        # for a symbol — otherwise an Iconify name match in the wrong sense produces
        # the "irrelevant/odd icon" look (see resolver._lookup step 4).
        image_src = await _resolve_image_src(
            session, content["visual"], color, allow_icon=scene.visual_kind == "icon"
        )
        layers: list[Layer] = []
        if llm is not None:
            try:
                draft = await llm.generate(_SYSTEM, _content_prompt(content), _SceneLayers)
                layers = _to_layers(draft.layers, image_src)
            except Exception:
                logger.warning("planner LLM failed for scene %s, using fallback", scene.id, exc_info=True)
        scene.layers = solve_layout(layers) if layers else fallback_layers(content, image_src)
        scene.elements = []  # content now lives in layers
    return document
