import sys

from api.sandbox.executor import SubprocessExecutor
from api.sandbox.types import SandboxLimits


async def test_runs_command_and_captures_output(tmp_path):
    executor = SubprocessExecutor()
    result = await executor.run(
        [sys.executable, "-c", "import sys; print('hello'); sys.stderr.write('warn')"],
        cwd=str(tmp_path),
        limits=SandboxLimits(timeout_s=10),
    )
    assert result.returncode == 0
    assert "hello" in result.stdout
    assert "warn" in result.stderr
    assert result.timed_out is False


async def test_nonzero_exit_is_reported(tmp_path):
    executor = SubprocessExecutor()
    result = await executor.run(
        [sys.executable, "-c", "import sys; sys.exit(3)"],
        cwd=str(tmp_path),
        limits=SandboxLimits(timeout_s=10),
    )
    assert result.returncode == 3
    assert result.timed_out is False


async def test_timeout_kills_the_process(tmp_path):
    executor = SubprocessExecutor()
    result = await executor.run(
        [sys.executable, "-c", "import time; time.sleep(5)"],
        cwd=str(tmp_path),
        limits=SandboxLimits(timeout_s=0.5),
    )
    assert result.timed_out is True
