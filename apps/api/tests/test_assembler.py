from collections.abc import Sequence

import pytest

from api.sandbox.types import ExecResult, RenderError, SandboxLimits
from api.visuals.assembler import Assembler


class FakeExecutor:
    def __init__(self, fail_index: int | None = None) -> None:
        self.commands: list[list[str]] = []
        self._fail_index = fail_index

    async def run(self, args: Sequence[str], *, cwd: str, limits: SandboxLimits) -> ExecResult:
        self.commands.append(list(args))
        out_path = args[-1]
        with open(out_path, "wb") as handle:
            handle.write(b"FINAL" if out_path.endswith("final.mp4") else b"SEG")
        if self._fail_index is not None and len(self.commands) - 1 == self._fail_index:
            return ExecResult(1, "", "boom")
        return ExecResult(0, "", "")


async def test_assembles_clips_into_final_video():
    executor = FakeExecutor()
    out = await Assembler(executor).assemble([(b"v0", b"a0"), (b"v1", b"a1")])

    assert out == b"FINAL"
    assert len(executor.commands) == 3  # two muxes + one concat
    assert executor.commands[-1][:4] == ["ffmpeg", "-y", "-f", "concat"]


async def test_raises_on_ffmpeg_failure():
    executor = FakeExecutor(fail_index=0)
    with pytest.raises(RenderError):
        await Assembler(executor).assemble([(b"v", b"a")])


async def test_empty_clips_raises():
    with pytest.raises(RenderError):
        await Assembler(FakeExecutor()).assemble([])
