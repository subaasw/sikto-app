import glob
import os
import shutil
import sys
import tempfile

from api.sandbox.executor import SubprocessExecutor
from api.sandbox.types import CommandExecutor, RenderError, RenderResult, SandboxLimits


class ManimRunner:
    """Renders an AI-generated Manim scene to video inside an ephemeral working
    directory. The command executor is injectable for testing."""

    def __init__(
        self,
        executor: CommandExecutor | None = None,
        *,
        limits: SandboxLimits | None = None,
        python_exe: str = sys.executable,
        quality_flag: str = "-qm",
    ) -> None:
        self._executor = executor or SubprocessExecutor()
        self._limits = limits or SandboxLimits()
        self._python = python_exe
        self._quality = quality_flag

    async def run(self, code: str, entry: str = "MainScene") -> RenderResult:
        workdir = tempfile.mkdtemp(prefix="sikto-manim-")
        try:
            with open(os.path.join(workdir, "scene.py"), "w", encoding="utf-8") as scene:
                scene.write(code)
            media_dir = os.path.join(workdir, "media")
            args = [
                self._python,
                "-m",
                "manim",
                "render",
                self._quality,
                "--media_dir",
                media_dir,
                "scene.py",
                entry,
            ]
            result = await self._executor.run(args, cwd=workdir, limits=self._limits)

            if result.timed_out:
                raise RenderError(
                    "manim render timed out", stdout=result.stdout, stderr=result.stderr
                )
            if result.returncode != 0:
                raise RenderError(
                    f"manim render failed (exit {result.returncode})",
                    stdout=result.stdout,
                    stderr=result.stderr,
                )

            video_path = _find_video(media_dir)
            if video_path is None:
                raise RenderError(
                    "manim produced no video output",
                    stdout=result.stdout,
                    stderr=result.stderr,
                )
            with open(video_path, "rb") as handle:
                video = handle.read()
            return RenderResult(video=video, stdout=result.stdout, stderr=result.stderr)
        finally:
            shutil.rmtree(workdir, ignore_errors=True)


def _find_video(media_dir: str) -> str | None:
    matches = sorted(glob.glob(os.path.join(media_dir, "videos", "**", "*.mp4"), recursive=True))
    return matches[-1] if matches else None
