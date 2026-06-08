from api.planning.schema import Segment, VisualType
from api.sandbox.types import RenderResult
from api.visuals.coder import CodeArtifact
from api.visuals.renderer import SegmentRenderer


class FakeCoder:
    def __init__(self, artifact: CodeArtifact) -> None:
        self._artifact = artifact

    async def generate(self, segment: Segment) -> CodeArtifact:
        return self._artifact


class FakeManim:
    def __init__(self) -> None:
        self.code: str | None = None

    async def run(self, code: str, entry: str = "MainScene") -> RenderResult:
        self.code = code
        return RenderResult(video=b"MANIM", stdout="", stderr="")


def _segment(visual_type: VisualType) -> Segment:
    return Segment(id="s0", order=0, narration="n", caption="c", visual_type=visual_type)


async def test_manim_segment_runs_on_manim_runner():
    coder = FakeCoder(CodeArtifact(runtime="manim", code="scene code", entry="MainScene"))
    manim = FakeManim()

    async def remotion(code: str, entry: str) -> bytes:
        raise AssertionError("remotion should not be called for a manim artifact")

    renderer = SegmentRenderer(coder, manim, remotion)
    video = await renderer.render_segment(_segment(VisualType.equation))

    assert video == b"MANIM"
    assert manim.code == "scene code"


async def test_remotion_segment_calls_remotion_render():
    coder = FakeCoder(CodeArtifact(runtime="remotion", code="comp code", entry="MainComposition"))
    seen: dict[str, str] = {}

    async def remotion(code: str, entry: str) -> bytes:
        seen["code"] = code
        seen["entry"] = entry
        return b"REMOTION"

    class BoomManim:
        async def run(self, code: str, entry: str = "MainScene") -> RenderResult:
            raise AssertionError("manim should not be called for a remotion artifact")

    renderer = SegmentRenderer(coder, BoomManim(), remotion)
    video = await renderer.render_segment(_segment(VisualType.bullet))

    assert video == b"REMOTION"
    assert seen == {"code": "comp code", "entry": "MainComposition"}
