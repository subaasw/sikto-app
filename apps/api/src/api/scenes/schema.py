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


# Spoken delivery styles, mapped to edge-tts prosody (rate/pitch) at synth time.
Delivery = Literal["neutral", "excited", "calm", "curious", "serious"]


class Narration(BaseModel):
    text: str
    caption: str | None = None
    delivery: Delivery = "neutral"


class SceneKind(StrEnum):
    slide = "slide"
    manim = "manim"


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
    # kind == "manim"
    manim_code: str | None = None
    manim_entry: str = "MainScene"


class SceneTheme(BaseModel):
    primary: str = "#84cc16"
    background: str = "#0c0e08"
    foreground: str = "#edf2e2"
    font: str = "Geist"
    template: str = "explainer"  # picks the render module (scene-kit templates/registry)
    background_style: Literal["gradient", "mesh", "grid", "solid", "texture"] = "gradient"
    element_style: Literal["plain", "sticker"] = "plain"  # sticker = cut-out border (marketing)
    sketch: bool = False  # hand-drawn (Rough.js) shapes/connectors — whiteboard look
    motion: Literal["smooth", "punchy", "sketch"] = "smooth"  # entrance style per template


class SceneDocument(BaseModel):
    version: int = 1
    title: str
    summary: str
    aspect_ratio: Literal["16:9", "9:16", "1:1"] = "16:9"
    theme: SceneTheme = Field(default_factory=SceneTheme)
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
        description="True if this beat is best shown as an animated equation (manim).",
    )
    needs_diagram: bool = Field(
        default=False,
        description=(
            "True if this beat is best shown as a labelled diagram of boxes and "
            "arrows (a process, hierarchy, or comparison) rather than bullet points."
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
