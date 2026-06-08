from collections.abc import Awaitable, Callable

from api.planning.schema import Segment
from api.sandbox.types import CodeRunner
from api.visuals.coder import MANIM, VisualCoder

# (code, entry) -> rendered mp4 bytes; in production this calls the apps/render service.
RemotionRenderFn = Callable[[str, str], Awaitable[bytes]]


class SegmentRenderer:
    """Turns a plan segment into a rendered video clip: generate code, then run it on the
    matching sandbox runner (Manim locally, Remotion via the render service)."""

    def __init__(
        self, coder: VisualCoder, manim: CodeRunner, remotion_render: RemotionRenderFn
    ) -> None:
        self._coder = coder
        self._manim = manim
        self._remotion_render = remotion_render

    async def render_segment(self, segment: Segment) -> bytes:
        artifact = await self._coder.generate(segment)
        if artifact.runtime == MANIM:
            result = await self._manim.run(artifact.code, artifact.entry)
            return result.video
        return await self._remotion_render(artifact.code, artifact.entry)
