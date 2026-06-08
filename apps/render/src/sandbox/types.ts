export interface ExecResult {
  code: number;
  stdout: string;
  stderr: string;
  timedOut: boolean;
}

export interface RenderResult {
  video: Buffer;
  stdout: string;
  stderr: string;
}

export interface Renderer {
  run(code: string, entry?: string): Promise<RenderResult>;
}

export type CommandExecutor = (
  args: string[],
  opts: { cwd: string; timeoutMs: number },
) => Promise<ExecResult>;

export class RenderError extends Error {
  stdout: string;
  stderr: string;
  constructor(message: string, opts: { stdout?: string; stderr?: string } = {}) {
    super(message);
    this.name = 'RenderError';
    this.stdout = opts.stdout ?? '';
    this.stderr = opts.stderr ?? '';
  }
}
