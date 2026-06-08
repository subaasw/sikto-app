from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol


@dataclass
class SandboxLimits:
    timeout_s: float = 120.0
    max_memory_mb: int = 1024
    max_output_mb: int = 256


@dataclass
class ExecResult:
    returncode: int
    stdout: str
    stderr: str
    timed_out: bool = False


@dataclass
class RenderResult:
    video: bytes
    stdout: str
    stderr: str


class RenderError(RuntimeError):
    def __init__(self, message: str, *, stdout: str = "", stderr: str = "") -> None:
        super().__init__(message)
        self.stdout = stdout
        self.stderr = stderr


class CommandExecutor(Protocol):
    async def run(self, args: Sequence[str], *, cwd: str, limits: SandboxLimits) -> ExecResult: ...


class CodeRunner(Protocol):
    async def run(self, code: str, entry: str) -> RenderResult: ...
