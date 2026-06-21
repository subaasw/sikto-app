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

from api.scenes.schema import Delivery, SceneTheme


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
        description="Clean, friendly lessons on a warm dark palette with soft gradients.",
        theme=SceneTheme(
            primary="#84cc16",
            background="#0c0e08",
            foreground="#edf2e2",
            font="Geist",
            background_style="gradient",
            motion="smooth",
        ),
        style=TemplateStyle(
            voice=(
                "Teach clearly and patiently, like a great tutor: define terms, give one "
                "concrete example per idea, and keep a calm, encouraging tone."
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
        description="Bold and energetic — punchy amber on deep indigo for high-impact videos.",
        theme=SceneTheme(
            primary="#f59e0b",
            background="#140a24",
            foreground="#faf5ff",
            font="Geist",
            background_style="mesh",
            motion="punchy",
        ),
        style=TemplateStyle(
            voice=(
                "Be punchy and benefit-driven, like a product launch: short, bold lines, "
                "active verbs, minimal jargon, and one big takeaway per beat. Lead with the "
                "payoff. Headings should read like confident claims, not labels."
            ),
            max_bullets=3,
            diagram_bias=(
                "Prefer bold single-idea slides over diagrams; only diagram a beat when it is "
                "an unmistakable before/after or step-by-step comparison."
            ),
            default_delivery="excited",
        ),
    ),
    "whiteboard": Template(
        id="whiteboard",
        name="Whiteboard",
        description="A hand-drawn feel: blue ink on paper with a subtle grid.",
        theme=SceneTheme(
            primary="#2563eb",
            background="#f4f1e8",
            foreground="#1f2937",
            font="Geist",
            background_style="grid",
            sketch=True,
            motion="sketch",
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
