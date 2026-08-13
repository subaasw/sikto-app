"""The declarative scene document.

A lesson is an ordered list of `Scene`s. A scene is either a declarative
`slide` (typed `Element`s the renderer draws) or a `manim` scene (generated
animation code for math/diagrams). Everything an editor or renderer needs is
data — no opaque code except the explicit `manim` escape hatch.
"""

from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, Field


class ElementType(StrEnum):
    heading = "heading"
    text = "text"
    bullets = "bullets"
    latex = "latex"
    image = "image"
    shape = "shape"
    code = "code"
    card = "card"  # a bordered, labelled box (a diagram node)
    character = "character"  # a procedural stick-figure presenter (lip-synced)


class Frame(BaseModel):
    """Normalised placement in the 0..1 unit square (0,0 = top-left)."""

    x: float = 0.08
    y: float = 0.12
    w: float = 0.84
    h: float = 0.2


class Element(BaseModel):
    id: str
    type: ElementType
    frame: Frame = Field(default_factory=Frame)
    z: int = 0
    text: str | None = None  # heading / text / code
    items: list[str] | None = None  # bullets
    latex: str | None = None  # latex
    src: str | None = None  # image
    shape: Literal["rect", "ellipse", "line", "arrow"] | None = None
    emphasis: list[str] | None = None  # key terms to highlight within text
    style: dict[str, Any] = Field(default_factory=dict)


class AnimationType(StrEnum):
    fade_in = "fade-in"
    reveal = "reveal"
    spotlight = "spotlight"
    pointer = "pointer"
    draw = "draw"  # a connector/line that draws itself in over its reveal window


class Animation(BaseModel):
    target_id: str
    type: AnimationType
    at_ms: int = 0
    duration_ms: int = 500


# --- Layer model (stop-motion renderer) ------------------------------------
# A slide scene is a back-to-front stack of semantic layers. The LLM composes
# them; the deterministic layout solver (scenes/layout.py) fills each `frame`.
# The LLM never emits coordinates.
LayerKind = Literal["image", "headline", "caption", "sticker", "shape", "bg-texture"]
Region = Literal[
    "full-bleed", "left", "right", "center", "upper", "lower", "upper-third", "lower-third"
]
LayerSize = Literal["sm", "md", "lg", "full"]
LayerMotion = Literal["pop", "drift", "settle", "none"]


class Layer(BaseModel):
    kind: LayerKind
    content: str | None = None  # text (headline/caption/sticker) | asset src (image) | shape name
    region: Region = "center"
    size: LayerSize = "md"
    depth: int = 1  # 0=back .. 2=front (parallax plane)
    motion: LayerMotion = "pop"
    frame: Frame | None = None  # filled by the layout solver; None until solved


# --- Whiteboard model (LLM-directed marker board) --------------------------
# A whiteboard scene is a choreographed storyboard of marks. Unlike the slide
# layer model, the brain is the DIRECTOR: it sets each mark's position (0..1) and
# its timing. The engine only clamps to the board — there is no layout solver and
# no deterministic fallback (a beat that can't be directed renders as a slide).
MarkKind = Literal["title", "write", "bullet", "box", "arrow", "underline", "sketch"]


class Mark(BaseModel):
    id: str
    kind: MarkKind
    text: str = ""
    frame: Frame = Field(default_factory=Frame)  # director-placed, clamped to 0..1
    ref: str | None = None  # arrow: source mark id
    to: str | None = None  # arrow: target mark id
    accent: bool = False  # draw in the accent marker colour
    at: float = 0.0  # when it starts drawing, 0..1 of the scene
    draw: float = 0.7  # seconds the stroke takes to draw on
    emphasis: bool = False  # pulse / highlight as the narration reaches it


# Spoken delivery styles, mapped to edge-tts prosody (rate/pitch) at synth time.
Delivery = Literal["neutral", "excited", "calm", "curious", "serious"]


class Narration(BaseModel):
    text: str
    caption: str | None = None
    delivery: Delivery = "neutral"


# --- marketing motion engine: intent (not pixels), physics generates the motion ---
MotionBeat = Literal["hook", "brand", "feature", "benefit", "stat", "social_proof", "cta"]
MotionMood = Literal["energetic", "bold", "playful", "calm"]
MotionRole = Literal["title", "sub", "chip", "icon", "stat", "cta"]
MotionEntrance = Literal["drop", "pop", "fly_in", "rise", "scatter"]  # a physics PROFILE
MotionAccent = Literal["confetti", "sparks", "none"]
MotionPaletteName = Literal["midnight", "sunset", "forest", "royal", "ember", "slate"]
MotionTextStyle = Literal["blur_up", "fade_up", "tracking_in", "spring_in"]
MotionBackground = Literal["mesh", "grid", "paper", "none"]
MotionOutro = Literal["wipe", "push", "frosted", "none"]
CameraDrift = Literal["left", "right", "up", "down", "none"]
CameraZoom = Literal["in", "out", "none"]
PlaneDepth = Literal["far", "mid", "near"]


class MotionCamera(BaseModel):
    """A gentle camera move — direction/kind only; the renderer owns the path."""

    drift: CameraDrift = "right"
    zoom: CameraZoom = "in"
    tilt_deg: float = Field(0.0, ge=-2.0, le=2.0)


class MotionPlane(BaseModel):
    """One parallax image plane. `query` is the search intent; the pipeline
    fills `src` via the media resolver (None -> renderer shows abstract art)."""

    query: str = ""
    depth: PlaneDepth = "mid"
    src: str | None = None


class MotionProp(BaseModel):
    """One thing on a marketing scene. The director picks role + entrance *feel*; the
    layout solver places it and the physics engine animates it (no x/y, no keyframes)."""

    content: str = ""  # on-screen text, or a resolved asset URL for role=icon
    role: MotionRole = "title"
    emphasis: int = Field(0, ge=0, le=2)
    entrance: MotionEntrance = "pop"


class MotionScene(BaseModel):
    """Semantic intent for a physics-driven, stepped stop-motion marketing scene."""

    beat: MotionBeat = "feature"
    mood: MotionMood = "energetic"
    props: list[MotionProp] = Field(default_factory=list)
    accent: MotionAccent = "none"
    palette: MotionPaletteName = "midnight"
    text_style: MotionTextStyle = "fade_up"
    background: MotionBackground = "mesh"
    outro: MotionOutro = "none"
    camera: MotionCamera = Field(default_factory=MotionCamera)
    planes: list[MotionPlane] = Field(default_factory=list, max_length=2)


class SceneKind(StrEnum):
    slide = "slide"
    manim = "manim"
    whiteboard = "whiteboard"
    diagram = "diagram"  # drawn boxes+arrows (cards/shapes in `elements`), not layers
    motion = "motion"  # physics-driven stop-motion marketing scene (`motion` field)


class Scene(BaseModel):
    id: str
    kind: SceneKind = SceneKind.slide
    duration_ms: int | None = None  # None → derived from narration audio length
    background: str | None = None
    narration: Narration
    # Art-direction intent from the LLM: what to depict on this scene. The
    # pipeline resolves it to an image. None → the director chose text-only.
    visual_query: str | None = None
    visual_kind: str | None = None
    # kind == "slide"
    elements: list[Element] = Field(default_factory=list)
    animations: list[Animation] = Field(default_factory=list)
    layers: list[Layer] = Field(default_factory=list)
    # kind == "manim"
    manim_code: str | None = None
    manim_entry: str = "MainScene"
    # kind == "whiteboard"
    marks: list[Mark] = Field(default_factory=list)
    # kind == "motion"
    motion: MotionScene | None = None


class Palette(BaseModel):
    """Role-based colors — mirrors packages/scene-kit/src/tokens.ts (keep in sync)."""

    bg: str  # canvas
    surface: str  # cards / panels
    ink: str  # primary text
    soft: str  # supporting text
    accent: str  # marker #1: underlines, arrows, emphasis
    accent2: str  # marker #2: circles, callouts
    accent_ink: str  # text set ON the accent (chips, CTAs)
    stroke: str  # frames, hairlines, connectors
    wash: str  # large tinted fields


class FontSet(BaseModel):
    display: str
    body: str
    script: str


Texture = Literal["graph", "grain", "none"]


class SceneTheme(BaseModel):
    primary: str = "#2563eb"
    background: str = "#f6f7f9"  # light whiteboard; the LLM director repaints this per video
    foreground: str = "#1f2937"
    font: str = "Geist"
    palette: Palette | None = None  # role tokens; legacy trio above still honoured
    fonts: FontSet | None = None
    texture: Texture | None = None
    template: str = "explainer"  # picks the render module (scene-kit templates/registry)
    background_style: Literal["gradient", "mesh", "grid", "solid", "texture"] = "gradient"
    element_style: Literal["plain", "sticker"] = "plain"  # sticker = cut-out border (marketing)
    sketch: bool = False  # hand-drawn (Rough.js) shapes/connectors — whiteboard look
    motion: Literal["smooth", "punchy", "sketch"] = "smooth"  # entrance style per template


# Video-level spoken energy, biased on top of each scene's `delivery` at synth time.
VoiceEnergy = Literal["calm", "balanced", "energetic", "hype"]


class VoiceProfile(BaseModel):
    """The narrator character for a whole video, chosen by the creative director."""

    voice: str = "en-US-AndrewNeural"  # resolved edge-tts voice
    energy: VoiceEnergy = "balanced"


class SceneDocument(BaseModel):
    version: int = 1
    title: str
    summary: str
    aspect_ratio: Literal["16:9", "9:16", "1:1"] = "16:9"
    theme: SceneTheme = Field(default_factory=SceneTheme)
    voice: VoiceProfile = Field(default_factory=VoiceProfile)
    scenes: list[Scene] = Field(min_length=1)
    profile: Literal["slide", "video"] = "video"  # course → slide, else video


# --- LLM-facing drafts -----------------------------------------------------
# The brain produces these simple, structured shapes; the engine assigns stable
# ids, lays out elements, and assembles the final SceneDocument.


class ResearchPlan(BaseModel):
    """Search queries the brain wants answered before outlining the lesson."""

    queries: list[str] = Field(
        default_factory=list,
        max_length=3,
        description="1-3 concise web search queries for material relevant to the lesson topic.",
    )


class CritiqueIssue(BaseModel):
    scene_id: str = Field(description="Id of the scene with the problem, e.g. 's2'.")
    problem: str = Field(description="One concrete, fixable flaw in this scene.")


class LessonCritique(BaseModel):
    """An editor's review of the assembled lesson for narrative quality."""

    issues: list[CritiqueIssue] = Field(
        default_factory=list,
        description="Real, fixable narrative problems. Empty when the lesson flows well.",
    )


# Layout archetypes the LLM art-director may assign to a plain text slide. Mirrors
# the layouts in scenes/assemble.py; 'auto' defers to the rule-based director.
ArchetypeName = Literal["presenter", "poster", "hero", "icon_grid", "plain", "auto"]


class SceneArt(BaseModel):
    scene_id: str = Field(description="Id of the scene to art-direct, e.g. 's0'.")
    archetype: ArchetypeName = Field(default="auto", description="The layout to use for this slide.")
    visual_query: str | None = Field(
        default=None,
        description="2-4 word concrete subject to illustrate (an object/scene), or null for text-only.",
    )


class ArtDirection(BaseModel):
    """The art-director's per-scene layout plan for a lesson's plain slides."""

    scenes: list[SceneArt] = Field(default_factory=list)


class OutlineBeat(BaseModel):
    title: str
    summary: str
    needs_math: bool = Field(
        default=False,
        description=(
            "True if this beat is best shown as an animated visualization (manim): an "
            "equation, graph/plot, geometric intuition, number line, transformation, or "
            "step-by-step build-up where the motion carries the meaning."
        ),
    )
    needs_diagram: bool = Field(
        default=False,
        description=(
            "True if this beat is best shown as a labelled diagram of boxes and "
            "arrows (a process, hierarchy, or comparison) rather than bullet points."
        ),
    )
    needs_whiteboard: bool = Field(
        default=False,
        description=(
            "True if this beat is best TAUGHT on a whiteboard: built up live, step "
            "by step (a derivation, worked example, intuition, or comparison), the "
            "way a teacher draws and annotates as they explain. Prefer this over a "
            "static diagram when the order things appear in carries the meaning."
        ),
    )


class LessonOutline(BaseModel):
    title: str
    summary: str
    beats: list[OutlineBeat] = Field(min_length=1, max_length=12)


class SlideDraft(BaseModel):
    """One slide's content, grounded in the source."""

    heading: str
    bullets: list[str] = Field(default_factory=list, max_length=6)
    latex: str | None = Field(default=None, description="Optional KaTeX expression to feature.")
    narration: str = Field(description="Spoken voiceover for this slide.")
    caption: str | None = None
    emphasis: list[str] = Field(
        default_factory=list,
        max_length=4,
        description="Up to 4 key words/phrases (verbatim from the heading or bullets) to highlight.",
    )
    delivery: Delivery = Field(
        default="neutral",
        description="Spoken tone that fits this slide: neutral, excited, calm, curious, or serious.",
    )
    visual: str | None = Field(
        default=None,
        description=(
            "A short phrase (2-4 words) naming a concrete image to illustrate this slide "
            "(e.g. 'rocket launch', 'brain neurons', 'team meeting'), or null if the slide "
            "is clearer as text only. You are the art director — choose imagery deliberately."
        ),
    )
    visual_kind: Literal["icon", "illustration", "auto"] = Field(
        default="auto",
        description="'icon' for a simple symbol, 'illustration' for a richer scene, else 'auto'.",
    )


class ManimDraft(BaseModel):
    """A math scene: self-contained Manim code plus its narration."""

    narration: str
    caption: str | None = None
    manim_code: str = Field(description="A self-contained Manim Scene subclass named MainScene.")


class DiagramDraft(BaseModel):
    """A labelled diagram the engine lays out from boxes and arrows.

    ``layout`` decides the arrangement; the engine assigns coordinates so the
    model never reasons about positions:

    - ``flow``: boxes left-to-right joined by arrows (a process or sequence).
    - ``stack``: boxes top-to-bottom joined by down-arrows (a hierarchy/steps).
    - ``compare``: a two-column grid of boxes, no arrows (X vs Y).
    """

    heading: str
    layout: Literal["flow", "stack", "compare"] = "flow"
    nodes: list[str] = Field(
        min_length=2, max_length=6, description="Short box labels, in order (max ~4 words each)."
    )
    connectors: list[str] = Field(
        default_factory=list,
        description=(
            "Optional labels for the arrows between consecutive nodes (flow/stack only). "
            "Provide one fewer than the number of nodes, or leave empty for unlabelled arrows."
        ),
    )
    narration: str = Field(description="Spoken voiceover explaining the diagram.")
    caption: str | None = None
    delivery: Delivery = Field(
        default="neutral",
        description="Spoken tone: neutral, excited, calm, curious, or serious.",
    )


class WhiteboardMark(BaseModel):
    """One directed mark on the board. The model is the motion-graphics director:
    it sets the position AND the timing of every mark — not just a bullet list."""

    kind: MarkKind = Field(
        description="title | write | bullet | box | arrow | underline | sketch."
    )
    text: str = Field("", description="Short on-board text. Empty for arrow/box-only marks.")
    x: float = Field(0.1, description="Left edge, 0..1 of the board (0=far left).")
    y: float = Field(0.15, description="Top edge, 0..1 of the board (0=top).")
    w: float = Field(0.35, description="Width, 0..1 of the board.")
    accent: bool = Field(False, description="Draw in the accent colour so it stands out.")
    emphasis: bool = Field(False, description="Pulse/highlight as the narration reaches it.")
    at: float = Field(0.0, description="When this mark starts drawing, 0..1 of the scene's length.")
    draw: float = Field(0.7, description="Seconds the draw-on stroke takes.")
    from_index: int | None = Field(
        None, description="kind='arrow' only: index (in this list) of the mark the arrow starts at."
    )
    to_index: int | None = Field(
        None, description="kind='arrow' only: index (in this list) of the mark the arrow points to."
    )


class WhiteboardDraft(BaseModel):
    """A whiteboard scene: a choreographed sequence of marks a teacher draws on a
    board, plus the spoken narration. The model directs both layout and timing."""

    marks: list[WhiteboardMark] = Field(min_length=1, max_length=12)
    narration: str = Field(description="Spoken voiceover for this scene.")
    caption: str | None = None
    delivery: Delivery = Field(default="neutral", description="Spoken tone.")
