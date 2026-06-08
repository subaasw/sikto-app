import os
import shutil
import tempfile
from collections.abc import Sequence

from api.sandbox.executor import SubprocessExecutor
from api.sandbox.types import CommandExecutor, RenderError, SandboxLimits


class Assembler:
    """Stitches per-segment video clips and narration audio into one lesson video using
    ffmpeg. Each clip is muxed with its audio, then all are concatenated. The command
    executor is injectable for testing."""

    def __init__(
        self,
        executor: CommandExecutor | None = None,
        *,
        ffmpeg: str = "ffmpeg",
        limits: SandboxLimits | None = None,
    ) -> None:
        self._executor = executor or SubprocessExecutor()
        self._ffmpeg = ffmpeg
        self._limits = limits or SandboxLimits()

    async def assemble(self, clips: Sequence[tuple[bytes, bytes]]) -> bytes:
        if not clips:
            raise RenderError("no clips to assemble")
        workdir = tempfile.mkdtemp(prefix="sikto-assemble-")
        try:
            segment_files: list[str] = []
            for index, (video, audio) in enumerate(clips):
                video_path = os.path.join(workdir, f"v{index}.mp4")
                audio_path = os.path.join(workdir, f"a{index}.m4a")
                seg_path = os.path.join(workdir, f"s{index}.mp4")
                _write(video_path, video)
                _write(audio_path, audio)
                await self._run(
                    [
                        self._ffmpeg,
                        "-y",
                        "-i",
                        video_path,
                        "-i",
                        audio_path,
                        "-c:v",
                        "copy",
                        "-c:a",
                        "aac",
                        "-map",
                        "0:v:0",
                        "-map",
                        "1:a:0",
                        "-shortest",
                        seg_path,
                    ],
                    workdir,
                )
                segment_files.append(seg_path)

            list_path = os.path.join(workdir, "list.txt")
            with open(list_path, "w", encoding="utf-8") as handle:
                for seg in segment_files:
                    handle.write(f"file '{os.path.basename(seg)}'\n")

            out_path = os.path.join(workdir, "final.mp4")
            await self._run(
                [
                    self._ffmpeg,
                    "-y",
                    "-f",
                    "concat",
                    "-safe",
                    "0",
                    "-i",
                    list_path,
                    "-c",
                    "copy",
                    out_path,
                ],
                workdir,
            )
            with open(out_path, "rb") as handle:
                return handle.read()
        finally:
            shutil.rmtree(workdir, ignore_errors=True)

    async def _run(self, args: list[str], cwd: str) -> None:
        result = await self._executor.run(args, cwd=cwd, limits=self._limits)
        if result.timed_out:
            raise RenderError("ffmpeg timed out", stdout=result.stdout, stderr=result.stderr)
        if result.returncode != 0:
            raise RenderError(
                f"ffmpeg failed (exit {result.returncode})",
                stdout=result.stdout,
                stderr=result.stderr,
            )


def _write(path: str, data: bytes) -> None:
    with open(path, "wb") as handle:
        handle.write(data)
