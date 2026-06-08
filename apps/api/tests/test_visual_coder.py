from api.planning.schema import Segment, VisualType
from api.visuals.coder import MANIM_SYSTEM, REMOTION_SYSTEM, VisualCoder


class FakeCoderLLM:
    def __init__(self, response: str) -> None:
        self.response = response
        self.seen: list[tuple[str, str]] = []

    async def complete(self, system: str, user: str) -> str:
        self.seen.append((system, user))
        return self.response


def _segment(visual_type: VisualType) -> Segment:
    return Segment(id="s0", order=0, narration="narration", caption="cap", visual_type=visual_type)


async def test_equation_routes_to_manim_and_strips_fences():
    llm = FakeCoderLLM("```python\nclass MainScene:\n    pass\n```")
    artifact = await VisualCoder(llm).generate(_segment(VisualType.equation))

    assert artifact.runtime == "manim"
    assert artifact.entry == "MainScene"
    assert artifact.code == "class MainScene:\n    pass"
    assert "```" not in artifact.code
    assert llm.seen[0][0] == MANIM_SYSTEM


async def test_diagram_routes_to_manim():
    artifact = await VisualCoder(FakeCoderLLM("class MainScene: ...")).generate(
        _segment(VisualType.diagram)
    )
    assert artifact.runtime == "manim"


async def test_bullet_routes_to_remotion():
    llm = FakeCoderLLM("export const MainComposition = () => null;")
    artifact = await VisualCoder(llm).generate(_segment(VisualType.bullet))

    assert artifact.runtime == "remotion"
    assert artifact.entry == "MainComposition"
    assert llm.seen[0][0] == REMOTION_SYSTEM
