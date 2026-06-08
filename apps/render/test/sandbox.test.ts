import assert from 'node:assert';
import { existsSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
import { test } from 'node:test';
import { RemotionRunner } from '../src/sandbox/remotion-runner.ts';
import type { CommandExecutor } from '../src/sandbox/types.ts';

test('writes composition + wrapper files and returns rendered bytes', async () => {
  let seenArgs: string[] = [];
  const stub: CommandExecutor = async (args, { cwd }) => {
    seenArgs = args;
    assert.ok(existsSync(join(cwd, 'Composition.tsx')), 'Composition.tsx written');
    assert.ok(existsSync(join(cwd, 'Root.tsx')), 'Root.tsx written');
    assert.ok(existsSync(join(cwd, 'index.ts')), 'index.ts written');
    writeFileSync(join(cwd, 'out.mp4'), Buffer.from('FAKEMP4'));
    return { code: 0, stdout: 'ok', stderr: '', timedOut: false };
  };

  const runner = new RemotionRunner(stub);
  const result = await runner.run('export const MainComposition = () => null;', 'MainComposition');

  assert.deepEqual(result.video, Buffer.from('FAKEMP4'));
  assert.ok(seenArgs.includes('--composition'));
  assert.ok(seenArgs.includes('MainComposition'));
});

test('throws on non-zero exit', async () => {
  const stub: CommandExecutor = async () => ({ code: 1, stdout: '', stderr: 'boom', timedOut: false });
  const runner = new RemotionRunner(stub);
  await assert.rejects(() => runner.run('code'), /remotion render failed/);
});

test('throws on timeout', async () => {
  const stub: CommandExecutor = async () => ({ code: -1, stdout: '', stderr: '', timedOut: true });
  const runner = new RemotionRunner(stub);
  await assert.rejects(() => runner.run('code'), /timed out/);
});
