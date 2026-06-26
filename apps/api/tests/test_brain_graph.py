"""Brain graph tests with a fake structured LLM — no network or API key."""

from collections.abc import Callable
from typing import TypeVar

from pydantic import BaseModel

from api.agent_engine.graph import generate_scene_document
from api.scenes.schema import (
    CritiqueIssue,
    ElementType,
    LessonCritique,
    LessonOutline,
    ManimDraft,
    OutlineBeat,
    SceneKind,
    SlideDraft,
)
from api.scenes.templates import get_template
from api.scenes.validation import validate_document

T = TypeVar("T", bound=BaseModel)


class FakeStructuredLLM:
    """Delegates each call to a handler: (schema, nth_call_for_schema) -> instance."""

    def __init__(self, handler: Callable[[type[BaseModel], int], BaseModel]) -> None:
        self._handler = handler
        self._counts: dict[str, int] = {}

    async def generate(self, system: str, user: str, schema: type[T]) -> T:
        self._counts[schema.__name__] = self._counts.get(schema.__name__, 0) + 1
        return self._handler(schema, self._counts[schema.__name__])  # type: ignore[return-value]


async def test_brain_builds_slide_and_manim_scenes():
    def handler(schema: type[BaseModel], n: int) -> BaseModel:
        if schema is LessonOutline:
            return LessonOutline(
                title="Cells",
                summary="The unit of life",
                beats=[
                    OutlineBeat(title="What is a cell", summary="basics"),
                    OutlineBeat(title="Membrane math", summary="diffusion", needs_math=True),
                ],
            )
        if schema is SlideDraft:
            return SlideDraft(heading="Cells", bullets=["tiny", "alive"], narration="A cell is...")
        if schema is ManimDraft:
            return ManimDraft(
                narration="Diffusion across the membrane.",
                manim_code="class MainScene(Scene):\n    def construct(self):\n        pass",
            )
        raise AssertionError(schema)

    doc = await generate_scene_document("source text", source_title="Bio", llm=FakeStructuredLLM(handler))

    assert doc.title == "Cells"
    assert [s.kind for s in doc.scenes] == [SceneKind.slide, SceneKind.manim]
    assert doc.scenes[1].manim_code
    assert validate_document(doc) == []


async def test_brain_repairs_invalid_scene():
    def handler(schema: type[BaseModel], n: int) -> BaseModel:
        if schema is LessonOutline:
            return LessonOutline(
                title="T", summary="S", beats=[OutlineBeat(title="b", summary="s")]
            )
        if schema is SlideDraft:
            # First compose attempt: empty narration → validation failure → repair.
            narration = "" if n == 1 else "now grounded and complete"
            return SlideDraft(heading="H", bullets=["a"], narration=narration)
        raise AssertionError(schema)

    llm = FakeStructuredLLM(handler)
    doc = await generate_scene_document("source", llm=llm, max_repairs=2)

    assert validate_document(doc) == []
    assert doc.scenes[0].narration.text == "now grounded and complete"


async def test_critique_feeds_the_repair_loop():
    """A clean-validating lesson still gets repaired when the editor flags a quality
    issue — proving the critique pass drives the same repair loop as the validator."""

    def handler(schema: type[BaseModel], n: int) -> BaseModel:
        if schema is LessonOutline:
            return LessonOutline(
                title="T", summary="S", beats=[OutlineBeat(title="b", summary="s")]
            )
        if schema is SlideDraft:
            return SlideDraft(heading="H", bullets=["a"], narration="first" if n == 1 else "revised")
        if schema is LessonCritique:
            # Flag s0 on the first review only; after repair, no further issues.
            return LessonCritique(
                issues=[CritiqueIssue(scene_id="s0", problem="repeats the intro")] if n == 1 else []
            )
        raise AssertionError(schema)

    doc = await generate_scene_document("source", llm=FakeStructuredLLM(handler), max_repairs=2)
    assert doc.scenes[0].narration.text == "revised"


async def test_vision_qa_feeds_the_repair_loop():
    """A reviewer that flags a visual defect drives the same repair loop — the scene
    is regenerated even though it validates and the editor found nothing."""

    class FakeVision:
        async def review(self, document):
            return ["scene s0: text overflows the card"]

    def handler(schema: type[BaseModel], n: int) -> BaseModel:
        if schema is LessonOutline:
            return LessonOutline(
                title="T", summary="S", beats=[OutlineBeat(title="b", summary="s")]
            )
        if schema is SlideDraft:
            return SlideDraft(heading="H", bullets=["a"], narration="first" if n == 1 else "revised")
        if schema is LessonCritique:
            return LessonCritique(issues=[])
        raise AssertionError(schema)

    doc = await generate_scene_document(
        "source", llm=FakeStructuredLLM(handler), vision=FakeVision(), max_repairs=2
    )
    assert doc.scenes[0].narration.text == "revised"


async def test_template_shapes_generation_structurally():
    """The same model output is reshaped by the template: marketing caps bullets at
    1 (minimal on-screen text) and stamps its 'excited' house tone; whiteboard keeps 4
    and goes 'calm'. Proves templates drive structure/delivery, not just colours."""

    def handler(schema: type[BaseModel], n: int) -> BaseModel:
        if schema is LessonOutline:
            return LessonOutline(
                title="T", summary="S", beats=[OutlineBeat(title="b", summary="s")]
            )
        if schema is SlideDraft:
            # Model emits 6 bullets and no strong tone (neutral) every time.
            return SlideDraft(
                heading="H",
                bullets=[f"point {i}" for i in range(6)],
                narration="grounded narration",
            )
        raise AssertionError(schema)

    def bullets_of(doc):
        # The engine emits one bullet element per point (and may split across scenes).
        return [e for s in doc.scenes for e in s.elements if e.type == ElementType.bullets]

    mkt = await generate_scene_document(
        "src", llm=FakeStructuredLLM(handler), template=get_template("marketing")
    )
    wb = await generate_scene_document(
        "src", llm=FakeStructuredLLM(handler), template=get_template("whiteboard")
    )

    assert len(bullets_of(mkt)) == 1 and mkt.scenes[0].narration.delivery == "excited"
    assert len(bullets_of(wb)) == 4 and wb.scenes[0].narration.delivery == "calm"
