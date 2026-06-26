import { existsSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import type { SceneAudio, SceneDocument } from '../remotion/schema.ts';
import { subprocessExecutor } from './executor.ts';
import { RenderError, type CommandExecutor, type RenderResult } from './types.ts';

const HERE = dirname(fileURLToPath(import.meta.url));
const WORKER = join(HERE, 'scene-worker.mjs');
const STILL_WORKER = join(HERE, 'scene-still-worker.mjs');
const ENTRY = join(HERE, '..', 'remotion', 'index.ts');

export interface SceneRenderOptions {
  audio?: SceneAudio[];
  manimClips?: Record<string, string>;
}

export interface SceneRenderer {
  render(document: SceneDocument, opts?: SceneRenderOptions): Promise<RenderResult>;
}

export interface SceneStiller {
  still(document: SceneDocument, sceneId: string): Promise<Buffer>;
}

/**
 * Renders the fixed `Lesson` Remotion composition with a SceneDocument supplied
 * as input props (no per-request codegen). Delegates the bundle+render to a
 * child worker; the executor is injectable for testing.
 */
export class RemotionSceneRenderer implements SceneRenderer {
  constructor(
    private readonly executor: CommandExecutor = subprocessExecutor,
    // A cold bundle + multi-scene lesson with audio can run for minutes. Kept
    // under the API's render_timeout_seconds so the API waits for our result.
    private readonly timeoutMs = 600_000,
  ) {}

  async render(document: SceneDocument, opts: SceneRenderOptions = {}): Promise<RenderResult> {
    const workdir = mkdtempSync(join(tmpdir(), 'sikto-scene-'));
    try {
      const propsPath = join(workdir, 'props.json');
      const outPath = join(workdir, 'out.mp4');
      writeFileSync(
        propsPath,
        JSON.stringify({
          document,
          audio: opts.audio ?? [],
          manim_clips: opts.manimClips ?? {},
        }),
        'utf8',
      );

      const result = await this.executor(
        ['node', WORKER, '--entry', ENTRY, '--props', propsPath, '--out', outPath, '--id', 'Lesson'],
        { cwd: workdir, timeoutMs: this.timeoutMs },
      );

      if (result.timedOut) throw new RenderError('scene render timed out', result);
      if (result.code !== 0) {
        throw new RenderError(`scene render failed (exit ${result.code})`, result);
      }
      if (!existsSync(outPath)) {
        throw new RenderError('scene render produced no video output', result);
      }
      return { video: readFileSync(outPath), stdout: result.stdout, stderr: result.stderr };
    } finally {
      rmSync(workdir, { recursive: true, force: true });
    }
  }
}

/**
 * Renders a single PNG still of one scene from the Lesson composition (a
 * mid-duration frame), for the API's Vision QA pass. Much cheaper than a full
 * video render but still a cold bundle + Chromium, so callers use it sparingly.
 */
export class RemotionSceneStiller implements SceneStiller {
  constructor(
    private readonly executor: CommandExecutor = subprocessExecutor,
    private readonly timeoutMs = 300_000,
  ) {}

  async still(document: SceneDocument, sceneId: string): Promise<Buffer> {
    const workdir = mkdtempSync(join(tmpdir(), 'sikto-still-'));
    try {
      const propsPath = join(workdir, 'props.json');
      const outPath = join(workdir, 'out.png');
      writeFileSync(propsPath, JSON.stringify({ document, audio: [], manim_clips: {} }), 'utf8');

      const result = await this.executor(
        ['node', STILL_WORKER, '--entry', ENTRY, '--props', propsPath, '--out', outPath, '--id', 'Lesson', '--scene', sceneId],
        { cwd: workdir, timeoutMs: this.timeoutMs },
      );

      if (result.timedOut) throw new RenderError('scene still timed out', result);
      if (result.code !== 0) throw new RenderError(`scene still failed (exit ${result.code})`, result);
      if (!existsSync(outPath)) throw new RenderError('scene still produced no image', result);
      return readFileSync(outPath);
    } finally {
      rmSync(workdir, { recursive: true, force: true });
    }
  }
}
