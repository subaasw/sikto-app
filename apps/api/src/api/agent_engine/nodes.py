"""Graph nodes for the brain. Each node is an async function of the state that
returns a partial update. LLM calls go through the injected `StructuredLLM`."""

import logging
from typing import Any

from api.agent_engine.llm import StructuredLLM
from api.agent_engine.research import NullSearch, WebSearch, format_research
from api.agent_engine.state import BrainState
from api.config import get_settings
from api.lesson_mode import DEFAULT_MODE, beat_bounds, mode_guidance
from api.scenes.assemble import diagram_scene, manim_scene, slide_scene
from api.scenes.schema import (
    DiagramDraft,
    LessonOutline,
    ManimDraft,
    OutlineBeat,
    ResearchPlan,
    Scene,
    SceneDocument,
    SlideDraft,
)
from api.scenes.templates import TemplateStyle, get_template
from api.scenes.validation import validate_document

logger = logging.getLogger("api.brain")

RESEARCH_SYSTEM = (
    "You are Sikto's research assistant. Read the source and propose 1-3 concise web "
    "search queries that would surface accurate, relevant background to teach this topic "
    "well. Prefer specific queries over broad ones. If the source is already complete and "
    "self-contained, return an empty list."
)

OUTLINE_SYSTEM = (
    "You are Sikto's lesson designer. Read the source (and any web research provided) and "
    "produce a tight microlearning outline: a title, a one-sentence summary, and a set of "
    "ordered beats. Each beat has a short title and summary. Scale the number of beats to the "
    "depth of the material — short sources get a few beats, rich sources get more. "
    "Set needs_math=true only when the beat is best shown as an animated equation. "
    "Set needs_diagram=true when the beat is best shown as a labelled diagram of boxes and "
    "arrows (a process, hierarchy, or comparison) rather than prose. Ground everything in "
    "the source; use the research only to organise and clarify, never to invent facts."
)

SLIDE_SYSTEM = (
    "You write one lesson slide grounded in the source. Give a short heading, up to 5 concise "
    "bullet points, and a natural spoken narration (2-4 sentences) that explains the slide. Leave "
    "'latex' null unless the beat is GENUINELY mathematical and a formula clarifies it — never put "
    "prose, 'None', or a placeholder there. In 'emphasis', list up to 4 key "
    "words/phrases copied VERBATIM from the heading or bullets that deserve visual highlight. "
    "Set 'delivery' to the spoken tone that best fits (neutral, excited, calm, curious, serious) "
    "so the voice-over feels alive. You are also the ART DIRECTOR: in 'visual', name a concrete "
    "image (2-4 words) that would illustrate this slide — prefer a vivid, depictable subject — or "
    "leave it null when the slide reads better as plain text. Set 'visual_kind' to 'icon' for a "
    "simple symbol or 'illustration' for a richer scene. Keep everything accurate to the source."
)

DIAGRAM_SYSTEM = (
    "You design one diagram for a lesson, grounded in the source. Choose a layout: 'flow' for "
    "a process or sequence (boxes left-to-right with arrows), 'stack' for a hierarchy or ordered "
    "steps (boxes top-to-bottom), or 'compare' for a side-by-side comparison (two columns, no "
    "arrows). Give 2-6 short node labels (max ~4 words each). For flow/stack you may add one "
    "connector label per arrow. Also write a natural spoken narration (2-4 sentences) and set "
    "'delivery' to the fitting tone (neutral, excited, calm, curious, serious). The engine "
    "positions the boxes — you only choose the layout, labels, narration, and delivery."
)

MANIM_SYSTEM = (
    "You write a self-contained Manim Community scene named MainScene that animates the beat's "
    "math, plus a spoken narration explaining it. Output only valid Manim Python in manim_code "
    "(no prose, no imports beyond manim). Do not access the network or filesystem."
)


def _target_beats(source_text: str, mode: str = DEFAULT_MODE) -> int:
    """Scale the lesson length to the source (~1 beat per 150 words), clamped to
    the mode's bounds — a short video stays tight, a course can run longer."""
    lo, hi = beat_bounds(mode)
    words = len(source_text.split())
    return max(lo, min(hi, round(words / 150) or lo))


def _styled(base: str, style: TemplateStyle) -> str:
    """Weave the template's editorial voice into a system prompt."""
    return f"{base}\n\nThis lesson's editorial style: {style.voice}"


def _source_prompt(
    state: BrainState, style: TemplateStyle | None = None, mode: str = DEFAULT_MODE
) -> str:
    title = state["source_title"] or "(untitled)"
    parts = [f"Source title: {title}", f"\nSource:\n{state['source_text']}"]
    if state.get("research"):
        parts.append(f"\nWeb research (relevant background, for structure only):\n{state['research']}")
    parts.append(f"\nFormat: {mode_guidance(mode)}")
    parts.append(f"\nAim for roughly {_target_beats(state['source_text'], mode)} beats.")
    if style and style.diagram_bias:
        parts.append(f"\nDiagram guidance: {style.diagram_bias}")
    return "\n".join(parts)


def _beat_prompt(state: BrainState, beat: OutlineBeat, feedback: str = "") -> str:
    base = (
        f"Lesson source title: {state['source_title'] or '(untitled)'}\n"
        f"Beat: {beat.title}\nBeat summary: {beat.summary}\n\n"
        f"Source excerpt:\n{state['source_text'][:6000]}"
    )
    if state.get("research"):
        base += f"\n\nWeb research (background, for accuracy only):\n{state['research'][:1200]}"
    return f"{base}\n\nFix these problems from the last attempt: {feedback}" if feedback else base


class BrainNodes:
    def __init__(
        self,
        llm: StructuredLLM,
        *,
        search: WebSearch | None = None,
        max_repairs: int = 2,
        style: TemplateStyle | None = None,
        mode: str = DEFAULT_MODE,
    ) -> None:
        self._llm = llm
        self._search = search or NullSearch()
        self._max_repairs = max_repairs
        self._style = style or get_template(None).style
        self._mode = mode

    async def research(self, state: BrainState) -> dict[str, Any]:
        # No real provider (tests / disabled) → skip the LLM call and the network.
        if isinstance(self._search, NullSearch):
            return {"research": ""}
        settings = get_settings()
        try:
            user = _source_prompt(state, self._style, self._mode)
            plan = await self._llm.generate(RESEARCH_SYSTEM, user, ResearchPlan)
            results = []
            for query in plan.queries[:3]:
                results.extend(await self._search.search(query, k=settings.web_search_results))
            research = format_research(results, max_chars=settings.web_search_max_chars)
            logger.info("brain research: %d queries, %d chars", len(plan.queries), len(research))
            return {"research": research}
        except Exception:  # best-effort: planning proceeds without research
            logger.warning("brain research step failed, continuing without it", exc_info=True)
            return {"research": ""}

    async def outline(self, state: BrainState) -> dict[str, Any]:
        outline = await self._llm.generate(
            _styled(OUTLINE_SYSTEM, self._style),
            _source_prompt(state, self._style, self._mode),
            LessonOutline,
        )
        logger.info("brain outline: %d beats", len(outline.beats))
        return {"outline": outline}

    async def _scene_for(self, index: int, state: BrainState, beat: OutlineBeat, fb: str) -> Scene:
        prompt = _beat_prompt(state, beat, fb)
        style = self._style
        if beat.needs_math:
            manim_draft = await self._llm.generate(MANIM_SYSTEM, prompt, ManimDraft)
            return manim_scene(index, manim_draft)
        if beat.needs_diagram:
            diagram_draft = await self._llm.generate(_styled(DIAGRAM_SYSTEM, style), prompt, DiagramDraft)
            return diagram_scene(index, self._apply_delivery(diagram_draft))
        slide_draft = await self._llm.generate(_styled(SLIDE_SYSTEM, style), prompt, SlideDraft)
        # Enforce the template's density cap and house delivery tone structurally,
        # so the lesson honours the style even if the model drifts past it.
        slide_draft = slide_draft.model_copy(update={"bullets": slide_draft.bullets[: style.max_bullets]})
        return slide_scene(index, self._apply_delivery(slide_draft))

    def _apply_delivery(self, draft: SlideDraft | DiagramDraft) -> Any:
        """Fill the template's house tone when the model left delivery neutral."""
        if draft.delivery == "neutral" and self._style.default_delivery != "neutral":
            return draft.model_copy(update={"delivery": self._style.default_delivery})
        return draft

    async def compose(self, state: BrainState) -> dict[str, Any]:
        outline = state["outline"]
        assert outline is not None
        scenes = [await self._scene_for(i, state, beat, "") for i, beat in enumerate(outline.beats)]
        document = SceneDocument(title=outline.title, summary=outline.summary, scenes=scenes)
        issues = validate_document(document)
        logger.info("brain compose: %d scenes, %d issues", len(scenes), len(issues))
        return {"document": document, "issues": issues}

    async def repair(self, state: BrainState) -> dict[str, Any]:
        outline = state["outline"]
        document = state["document"]
        assert outline is not None and document is not None
        bad = {
            issue.split(":", 1)[0].removeprefix("scene ").strip()
            for issue in state["issues"]
            if issue.startswith("scene ")
        }
        scenes = list(document.scenes)
        for index, beat in enumerate(outline.beats):
            sid = f"s{index}"
            if sid not in bad:
                continue
            feedback = " ".join(i for i in state["issues"] if i.startswith(f"scene {sid}"))
            scenes[index] = await self._scene_for(index, state, beat, feedback)
        repaired = document.model_copy(update={"scenes": scenes})
        issues = validate_document(repaired)
        logger.info("brain repair #%d: %d issues remain", state["repairs"] + 1, len(issues))
        return {"document": repaired, "issues": issues, "repairs": state["repairs"] + 1}

    def route(self, state: BrainState) -> str:
        if state["issues"] and state["repairs"] < self._max_repairs:
            return "repair"
        return "done"
