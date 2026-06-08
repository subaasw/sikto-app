import { existsSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { subprocessExecutor } from './executor.ts';
import { RenderError, type CommandExecutor, type RenderResult } from './types.ts';

const WORKER = join(dirname(fileURLToPath(import.meta.url)), 'render-worker.mjs');

const ROOT_TSX = `import { Composition } from 'remotion';
import { MainComposition } from './Composition';

export const RemotionRoot = () => (
  <Composition
    id="MainComposition"
    component={MainComposition}
    durationInFrames={150}
    fps={30}
    width={1920}
    height={1080}
  />
);
`;

const INDEX_TS = `import { registerRoot } from 'remotion';
import { RemotionRoot } from './Root';

registerRoot(RemotionRoot);
`;

/**
 * Runs an AI-generated Remotion composition to an mp4 inside an ephemeral working
 * directory via a child render worker. The executor is injectable for testing.
 * The AI code must export a component named `MainComposition`.
 */
export class RemotionRunner {
  constructor(
    private readonly executor: CommandExecutor = subprocessExecutor,
    private readonly timeoutMs = 120_000,
  ) {}

  async run(code: string, entry = 'MainComposition'): Promise<RenderResult> {
    const workdir = mkdtempSync(join(tmpdir(), 'sikto-remotion-'));
    try {
      writeFileSync(join(workdir, 'Composition.tsx'), code, 'utf8');
      writeFileSync(join(workdir, 'Root.tsx'), ROOT_TSX, 'utf8');
      writeFileSync(join(workdir, 'index.ts'), INDEX_TS, 'utf8');
      const outPath = join(workdir, 'out.mp4');

      const result = await this.executor(
        ['node', WORKER, '--workdir', workdir, '--composition', entry, '--out', outPath],
        { cwd: workdir, timeoutMs: this.timeoutMs },
      );

      if (result.timedOut) throw new RenderError('remotion render timed out', result);
      if (result.code !== 0) {
        throw new RenderError(`remotion render failed (exit ${result.code})`, result);
      }
      if (!existsSync(outPath)) {
        throw new RenderError('remotion produced no video output', result);
      }
      return { video: readFileSync(outPath), stdout: result.stdout, stderr: result.stderr };
    } finally {
      rmSync(workdir, { recursive: true, force: true });
    }
  }
}
