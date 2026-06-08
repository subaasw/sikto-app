import { spawn } from 'node:child_process';
import type { CommandExecutor, ExecResult } from './types.ts';

// Local-grade isolation: a child process with a hard timeout, args passed as a list
// (no shell). Production should run the same worker inside a container.
export const subprocessExecutor: CommandExecutor = (args, { cwd, timeoutMs }) =>
  new Promise<ExecResult>((resolve) => {
    const [command, ...rest] = args;
    const child = spawn(command, rest, { cwd });

    let stdout = '';
    let stderr = '';
    let timedOut = false;

    const timer = setTimeout(() => {
      timedOut = true;
      child.kill('SIGKILL');
    }, timeoutMs);

    child.stdout.on('data', (chunk) => (stdout += chunk.toString()));
    child.stderr.on('data', (chunk) => (stderr += chunk.toString()));
    child.on('error', (err) => {
      clearTimeout(timer);
      resolve({ code: -1, stdout, stderr: stderr + String(err), timedOut });
    });
    child.on('close', (code) => {
      clearTimeout(timer);
      resolve({ code: code ?? -1, stdout, stderr, timedOut });
    });
  });
