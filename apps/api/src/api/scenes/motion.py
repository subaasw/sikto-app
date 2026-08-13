"""Marketing motion director: turn slide scenes into remocn/Remotion `motion` scenes.

The director only chooses *intent* — beat, copy, and STYLE (palette/text
animation/background/outro/camera/image planes), every field an enum or a
clamped number. The scene-kit/motion-kit renderer owns all pixels and paths.
Deterministic by default so a marketing lesson looks art-directed even with no
LLM configured; an LLM director layers real per-scene choices on top.
"""

import logging

from pydantic import BaseModel, Field

from api.agent_engine.llm import StructuredLLM
from api.media.resolver import resolve_asset
from api.scenes.planner import scene_content
from api.scenes.schema import (
    CameraDrift,
    MotionAccent,
    MotionBackground,
    MotionBeat,
    MotionCamera,
    MotionEntrance,
    MotionMood,
    MotionOutro,
    MotionPaletteName,
    MotionPlane,
    MotionProp,
    MotionRole,
    MotionScene,
    MotionTextStyle,
    PlaneDepth,
    SceneDocument,
    SceneKind,
)

logger = logging.getLogger("api.motion")

# entrance feel per beat — keeps each beat visually distinct without LLM input.
_TITLE_ENTRANCE = {
    "hook": "pop",
    "brand": "drop",
    "feature": "rise",
    "benefit": "fly_in",
    "stat": "drop",
    "social_proof": "scatter",
    "cta": "pop",
}
_ACCENT: dict[str, MotionAccent] = {"cta": "confetti", "hook": "sparks", "stat": "sparks"}
# short eyebrow label per beat — sentence case (anti-slop: never ALL-CAPS).
_CHIP = {
    "hook": "Why it matters",
    "brand": "Meet the tool",
    "feature": "How it works",
    "benefit": "The payoff",
    "stat": "By the numbers",
    "social_proof": "Loved by teams",
    "cta": "Your move",
}
# deterministic style per beat/index so a no-LLM lesson still feels art-directed.
_PALETTE: dict[str, MotionPaletteName] = {
    "hook": "midnight",
    "brand": "royal",
    "feature": "slate",
    "benefit": "forest",
    "stat": "ember",
    "social_proof": "sunset",
    "cta": "midnight",
}
_TEXT_STYLE: dict[str, MotionTextStyle] = {
    "hook": "spring_in",
    "brand": "tracking_in",
    "feature": "fade_up",
    "benefit": "fade_up",
    "stat": "blur_up",
    "social_proof": "fade_up",
    "cta": "spring_in",
}
_DRIFTS: tuple[CameraDrift, ...] = ("right", "left", "up", "down")
_OUTROS: tuple[MotionOutro, ...] = ("wipe", "push", "frosted")


def _beat_for(index: int, total: int, heading: str) -> MotionBeat:
    if index == 0:
        return "hook"
    if index >= total - 1:
        return "cta"
    if any(ch.isdigit() for ch in heading):
        return "stat"
    return "feature" if index % 2 else "benefit"


def fallback_motion(content: dict, index: int, total: int) -> MotionScene:
    """Deterministic intent from a slide's heading/bullets. Never empty."""
    heading = content["heading"] or content["body"] or "..."
    beat = _beat_for(index, total, heading)
    mood = "bold" if beat in ("hook", "cta") else "energetic"
    sub = content["bullets"][0] if content["bullets"] else content["body"]
    props: list[MotionProp] = [
        MotionProp(content=_CHIP[beat], role="chip", emphasis=1, entrance="rise"),
        MotionProp(content=heading, role="title", emphasis=2, entrance=_TITLE_ENTRANCE[beat]),
    ]
    if beat == "cta":
        props.append(MotionProp(content=sub or "Get started", role="cta", emphasis=2, entrance="drop"))
    elif sub and sub.strip() != heading.strip():
        # one supporting line, and only when it says something the headline doesn't
        props.append(MotionProp(content=sub, role="sub", emphasis=1, entrance="rise"))
    # keep it to at most three lines — a badge, a headline, and one supporting line
    return MotionScene(
        beat=beat,
        mood=mood,
        props=props[:3],
        accent=_ACCENT.get(beat, "none"),
        palette=_PALETTE[beat],
        text_style=_TEXT_STYLE[beat],
        background="mesh" if beat in ("hook", "brand", "cta") else "paper" if beat in ("benefit", "social_proof") else "grid",
        outro="none" if index >= total - 1 else _OUTROS[index % len(_OUTROS)],
        camera=MotionCamera(
            drift=_DRIFTS[index % len(_DRIFTS)],
            zoom="in" if index % 2 == 0 else "out",
            tilt_deg=(-1.2, 0.0, 1.2)[index % 3],
        ),
    )


# --- LLM direction: style only, one call for the whole video -------------------

_MOTION_SYSTEM = (
    "You are the art director for a short, professional MARKETING motion video. "
    "For EACH scene, in order, pick a look and rhythm that fits the copy: a palette, "
    "a text animation style, a background, an exit, a gentle camera move, and at most "
    "one image idea (a short search query, or empty). You choose STYLE ONLY from the "
    "allowed values — never pixels, coordinates, or colors. Copy rules: a short "
    "sentence-case chip, a punchy title, and at most one supporting line (a cta line "
    "only on the closing scene); lines must not repeat each other. Vary palette, "
    "text_style and camera across scenes so the video feels art-directed, not "
    "templated, while keeping a coherent overall feel. Background 'paper' is a "
    "hand-crafted paper-cutout collage \u2014 pick it for playful or human beats."
)


class _DirectedProp(BaseModel):
    content: str = Field("", max_length=120)
    role: MotionRole = "title"
    emphasis: int = Field(1, ge=0, le=2)
    entrance: MotionEntrance = "pop"


class _MotionDirection(BaseModel):
    beat: MotionBeat = "feature"
    mood: MotionMood = "energetic"
    palette: MotionPaletteName = "midnight"
    text_style: MotionTextStyle = "fade_up"
    background: MotionBackground = "mesh"
    outro: MotionOutro = "none"
    camera: MotionCamera = Field(default_factory=MotionCamera)
    image_query: str = Field("", max_length=80, description="one short image search query, or empty")
    image_depth: PlaneDepth = "mid"
    props: list[_DirectedProp] = Field(default_factory=list, max_length=3)


class _MotionDirectionList(BaseModel):
    scenes: list[_MotionDirection] = Field(default_factory=list)


def _to_motion(d: _MotionDirection) -> MotionScene | None:
    props = [
        MotionProp(content=p.content, role=p.role, emphasis=p.emphasis, entrance=p.entrance)
        for p in d.props
        if p.content.strip()
    ]
    if not any(p.role == "title" for p in props):
        return None  # a directed scene without a title is unusable — fall back
    planes = [MotionPlane(query=d.image_query.strip(), depth=d.image_depth)] if d.image_query.strip() else []
    return MotionScene(
        beat=d.beat,
        mood=d.mood,
        props=props[:3],
        accent=_ACCENT.get(d.beat, "none"),
        palette=d.palette,
        text_style=d.text_style,
        background=d.background,
        outro=d.outro,
        camera=d.camera,
        planes=planes,
    )


async def plan_motion(
    document: SceneDocument,
    *,
    llm: StructuredLLM | None = None,
    session=None,
) -> SceneDocument:
    """Convert each slide scene into a `motion` scene (marketing template).
    LLM art-directs style when available; deterministic fallback otherwise.
    With a DB session, image planes resolve to real assets. Best-effort throughout."""
    slides = [s for s in document.scenes if s.kind == SceneKind.slide]
    total = len(slides)
    if not total:
        return document
    contents = [scene_content(s) for s in slides]
    directed: list[MotionScene | None] = [None] * total
    if llm is not None:
        try:
            user = "\n\n".join(
                f"Scene {i + 1} of {total}\nHeading: {c['heading']}\n"
                f"Support: {c['bullets'][0] if c['bullets'] else c['body']}"
                for i, c in enumerate(contents)
            )
            d = await llm.generate(_MOTION_SYSTEM, user, _MotionDirectionList)
            for i, item in enumerate(d.scenes[:total]):
                directed[i] = _to_motion(item)
        except Exception:
            logger.warning("motion direction failed, using fallback", exc_info=True)
    for i, scene in enumerate(slides):
        motion = directed[i] or fallback_motion(contents[i], i, total)
        if not motion.planes and scene.visual_query:
            # the brain already picked an image intent for this slide — reuse it
            motion.planes = [MotionPlane(query=scene.visual_query, depth="mid")]
        scene.motion = motion
        scene.kind = SceneKind.motion
        scene.elements = []  # content now lives in the motion props
        scene.layers = []
    if session is not None:
        registry: dict = {}
        for scene in slides:
            for plane in scene.motion.planes:
                if not plane.query or plane.src:
                    continue
                try:
                    # photos read best on the dark marketing canvas; never mono icons
                    asset = await resolve_asset(
                        session, plane.query, registry=registry, prefer_photo=True, allow_icon=False
                    )
                    plane.src = asset.url if asset else None
                except Exception:
                    logger.warning("plane asset failed for %r", plane.query, exc_info=True)
    return document
