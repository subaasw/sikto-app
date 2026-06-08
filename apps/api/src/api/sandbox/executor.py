import asyncio
import contextlib
import sys
from collections.abc import Callable, Sequence

from api.sandbox.types import ExecResult, SandboxLimits


class SubprocessExecutor:
    """Runs a command in a child process with a hard timeout and (POSIX) resource
    limits. Commands are passed as an argument list (no shell), so there is no shell
    injection surface. This is local-grade isolation; production should run the same
    command inside a container."""

    async def run(self, args: Sequence[str], *, cwd: str, limits: SandboxLimits) -> ExecResult:
        preexec = _resource_limiter(limits) if sys.platform != "win32" else None
        process = await asyncio.create_subprocess_exec(
            *args,
            cwd=cwd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            preexec_fn=preexec,
        )
        try:
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=limits.timeout_s)
        except TimeoutError:
            process.kill()
            await process.wait()
            return ExecResult(
                returncode=-9, stdout="", stderr="execution timed out", timed_out=True
            )

        return ExecResult(
            returncode=process.returncode if process.returncode is not None else -1,
            stdout=stdout.decode(errors="replace"),
            stderr=stderr.decode(errors="replace"),
        )


def _resource_limiter(limits: SandboxLimits) -> Callable[[], None]:
    import resource

    def _apply() -> None:
        cpu_seconds = int(limits.timeout_s) + 1
        _try_setrlimit(resource.RLIMIT_CPU, cpu_seconds)
        _try_setrlimit(resource.RLIMIT_FSIZE, limits.max_output_mb * 1024 * 1024)
        _try_setrlimit(resource.RLIMIT_AS, limits.max_memory_mb * 1024 * 1024)

    def _try_setrlimit(which: int, value: int) -> None:
        # Some limits aren't enforceable on every platform; skip rather than fail.
        with contextlib.suppress(ValueError, OSError):
            resource.setrlimit(which, (value, value))

    return _apply
