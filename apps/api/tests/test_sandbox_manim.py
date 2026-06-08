import os
from collections.abc import Sequence

import pytest

from api.sandbox.manim import ManimRunner
from api.sandbox.types import ExecResult, RenderError, SandboxLimits


class FakeExecutor:
    def __init__(self, result: ExecResult, *, make_output: bool = False) -> None:
        self._result = result
        self._make_output = make_output
        self.calls: list[list[str]] = []

    async def run(self, args: Sequence[str], *, cwd: str, limits: SandboxLimits) -> ExecResult:
        self.calls.append(list(args))
        if self._make_output:
            out_dir = os.path.join(cwd, "media", "videos", "scene", "720p30")
            os.makedirs(out_dir, exist_ok=True)
            with open(os.path.join(out_dir, "MainScene.mp4"), "wb") as handle:
                handle.write(b"FAKEMP4")
        return self._result


async def test_manim_runner_returns_video_bytes():
    executor = FakeExecutor(ExecResult(0, "rendered", ""), make_output=True)
    result = await ManimRunner(executor).run("print('scene')", "MainScene")

    assert result.video == b"FAKEMP4"
    assert result.stdout == "rendered"
    assert executor.calls[0][1:4] == ["-m", "manim", "render"]
    assert executor.calls[0][-2:] == ["scene.py", "MainScene"]


async def test_manim_runner_raises_on_nonzero_exit():
    executor = FakeExecutor(ExecResult(1, "", "boom"))
    with pytest.raises(RenderError):
        await ManimRunner(executor).run("code")


async def test_manim_runner_raises_on_timeout():
    executor = FakeExecutor(ExecResult(-9, "", "", timed_out=True))
    with pytest.raises(RenderError):
        await ManimRunner(executor).run("code")


async def test_manim_runner_raises_when_no_video_produced():
    executor = FakeExecutor(ExecResult(0, "ok", ""), make_output=False)
    with pytest.raises(RenderError):
        await ManimRunner(executor).run("code")
