import json
from dataclasses import dataclass
from typing import Protocol

from api.planning.schema import Segment, VisualType

MANIM = "manim"
REMOTION = "remotion"

_MANIM_VISUALS = {VisualType.equation, VisualType.diagram}


@dataclass
class CodeArtifact:
    runtime: str  # "manim" | "remotion"
    code: str
    entry: str  # scene class (manim) / composition id (remotion)


class CoderLLM(Protocol):
    async def complete(self, system: str, user: str) -> str: ...


MANIM_SYSTEM = (
    "You write Manim Community Edition Python code. Given a lesson segment, output a single "
    "self-contained Manim Scene subclass named MainScene that visually illustrates it. Keep it "
    "short. Do NOT access the network or filesystem. Output ONLY Python code: no prose, no fences."
)

REMOTION_SYSTEM = (
    "You write a Remotion composition in TypeScript/TSX. Output a single named export "
    "`MainComposition` (a React function component) that visually presents the segment using "
    "Remotion primitives. Keep it self-contained. Do NOT access the network or filesystem. "
    "Output ONLY TSX code: no prose, no fences."
)


class VisualCoder:
    """Generates the animation code for a segment, routed to Manim (math/diagram) or
    Remotion (everything else) by the segment's visual type."""

    def __init__(
        self,
        llm: CoderLLM,
        *,
        manim_entry: str = "MainScene",
        remotion_entry: str = "MainComposition",
    ) -> None:
        self._llm = llm
        self._manim_entry = manim_entry
        self._remotion_entry = remotion_entry

    async def generate(self, segment: Segment) -> CodeArtifact:
        use_manim = segment.visual_type in _MANIM_VISUALS
        system = MANIM_SYSTEM if use_manim else REMOTION_SYSTEM
        raw = await self._llm.complete(system, _segment_prompt(segment))
        return CodeArtifact(
            runtime=MANIM if use_manim else REMOTION,
            code=_strip_code_fences(raw),
            entry=self._manim_entry if use_manim else self._remotion_entry,
        )


def _segment_prompt(segment: Segment) -> str:
    return (
        f"Visual type: {segment.visual_type.value}\n"
        f"Caption: {segment.caption}\n"
        f"Narration: {segment.narration}\n"
        f"Hints: {json.dumps(segment.render_hints)}"
    )


def _strip_code_fences(raw: str) -> str:
    text = raw.strip()
    if not text.startswith("```"):
        return text
    lines = text.splitlines()
    if lines and lines[0].startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].strip().startswith("```"):
        lines = lines[:-1]
    return "\n".join(lines).strip()
