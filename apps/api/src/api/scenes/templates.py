"""Lesson templates: not just a palette, but an editorial style the brain
generates *into*.

A template carries two halves:

- ``theme``  — the visual paint (palette + background) the renderer applies.
- ``style``  — real generation knobs the brain reads: an editorial voice woven
  into its prompts, a bullet-density cap it enforces structurally, a bias toward
  (or away from) diagrams, and a house delivery tone for the narration.

So an "explainer", "marketing", and "whiteboard" run of the same source produce
genuinely different lessons — different pacing, density, structure, and voice —
not the same lesson in different colours. The default is ``explainer``.
"""

from typing import get_args

from pydantic import BaseModel

from api.scenes.schema import Delivery, FontSet, Palette, SceneTheme


class TemplateStyle(BaseModel):
    """Editorial knobs the brain honours while generating the lesson."""

    voice: str  # directive woven into the outline/slide/diagram system prompts
    max_bullets: int = 5  # hard cap on bullets per slide (structural)
    diagram_bias: str = ""  # outline guidance: lean toward / away from diagrams
    default_delivery: Delivery = "neutral"  # house tone when the model picks none


class Template(BaseModel):
    id: str
    name: str
    description: str
    theme: SceneTheme
    style: TemplateStyle


TEMPLATES: dict[str, Template] = {
    "explainer": Template(
        id="explainer",
        name="Explainer",
        description="Clean, modern lessons: emerald marker on a clean board, hand-drawn headings.",
        theme=SceneTheme(
            primary="#0c7a58",
            background="#f4f6f2",
            foreground="#1b2a24",
            font="Geist",
            template="explainer",
            background_style="solid",
            motion="smooth",
            palette=Palette(
                bg="#f4f6f2",
                surface="#ffffff",
                ink="#1b2a24",
                soft="#51645b",
                accent="#0c7a58",
                accent2="#c2542e",
                accent_ink="#ffffff",
                stroke="#9db0a6",
                wash="#e3ede6",
            ),
            fonts=FontSet(
                display='"Bricolage Grotesque", Geist, sans-serif',
                body="Geist, sans-serif",
                script='"Caveat", cursive',
            ),
            texture="graph",
        ),
        style=TemplateStyle(
            voice=(
                "Teach clearly and patiently, like a great tutor: define terms, give one "
                "concrete example per idea, and keep a calm, encouraging tone. Make it "
                "visual: for most slides choose one concrete icon or simple illustration "
                "that represents the idea, so the lesson shows as much as it tells."
            ),
            max_bullets=5,
            diagram_bias=(
                "Use a diagram when the beat is genuinely a process, hierarchy, or comparison; "
                "otherwise a slide is fine."
            ),
            default_delivery="neutral",
        ),
    ),
    "marketing": Template(
        id="marketing",
        name="Marketing",
        description="Bold and high-impact — confident orange marker on a clean board for launch-style videos.",
        theme=SceneTheme(
            primary="#f4b642",
            background="#171112",
            foreground="#faeeea",
            font="Geist",
            template="marketing",
            background_style="solid",
            element_style="sticker",
            motion="punchy",
            palette=Palette(
                bg="#171112",
                surface="#26191b",
                ink="#faeeea",
                soft="#c9a29b",
                accent="#f4b642",
                accent2="#ff8a5c",
                accent_ink="#231505",
                stroke="#4a3a35",
                wash="#26191b",
            ),
            fonts=FontSet(
                display='"Archivo Black", Geist, sans-serif',
                body="Geist, sans-serif",
                script='"Caveat", cursive',
            ),
            texture="grain",
        ),
        style=TemplateStyle(
            voice=(
                "Be punchy and benefit-driven, like a product launch. Each beat is ONE bold "
                "headline that reads like a confident claim, not a label — no bullet lists, no "
                "paragraphs on screen. Keep on-screen text to that single line and let the "
                "narration carry the detail. Always name a vivid, concrete visual (a real "
                "object, scene, or character) that could fill the whole frame."
            ),
            max_bullets=1,
            diagram_bias=(
                "Prefer one bold visual per beat over diagrams; only diagram a beat when it is "
                "an unmistakable before/after or step-by-step comparison."
            ),
            default_delivery="excited",
        ),
    ),
    "whiteboard": Template(
        id="whiteboard",
        name="Whiteboard",
        description="A hand-drawn feel: blue marker drawn onto a clean white board.",
        theme=SceneTheme(
            primary="#2456c9",
            background="#f8fafc",
            foreground="#1e2937",
            font="Geist",
            template="whiteboard",
            background_style="solid",
            sketch=True,
            motion="sketch",
            palette=Palette(
                bg="#f8fafc",
                surface="#ffffff",
                ink="#1e2937",
                soft="#5a6b7d",
                accent="#2456c9",
                accent2="#cc4444",
                accent_ink="#ffffff",
                stroke="#93a3b3",
                wash="#e7eef7",
            ),
            fonts=FontSet(
                display='"Caveat", cursive',
                body="Geist, sans-serif",
                script='"Caveat", cursive',
            ),
            texture="grain",
        ),
        style=TemplateStyle(
            voice=(
                "Explain step by step as if sketching on a whiteboard: build each idea "
                "incrementally, name the parts, and connect them so the structure is visible. "
                "Favour showing how things relate over listing facts."
            ),
            max_bullets=4,
            diagram_bias=(
                "Lean toward diagrams: whenever a beat involves a process, sequence, hierarchy, "
                "or comparison, mark it as a diagram rather than bullets."
            ),
            default_delivery="calm",
        ),
    ),
}

assert all(t.style.default_delivery in get_args(Delivery) for t in TEMPLATES.values())

DEFAULT_TEMPLATE = "explainer"


def get_template(name: str | None) -> Template:
    return TEMPLATES.get(name or DEFAULT_TEMPLATE, TEMPLATES[DEFAULT_TEMPLATE])
