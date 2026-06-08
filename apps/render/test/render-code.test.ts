import assert from 'node:assert';
import { test } from 'node:test';
import { build } from '../src/server.ts';
import type { Renderer } from '../src/sandbox/types.ts';

test('render-code returns base64 video from the runner', async () => {
  const fakeRunner: Renderer = {
    run: async () => ({ video: Buffer.from('CLIP'), stdout: '', stderr: '' }),
  };
  const app = build(fakeRunner);
  const res = await app.inject({
    method: 'POST',
    url: '/render-code',
    payload: { code: 'export const MainComposition = () => null;', composition: 'MainComposition' },
  });

  assert.equal(res.statusCode, 200);
  assert.equal(Buffer.from(res.json().video_b64, 'base64').toString(), 'CLIP');
});

test('render-code requires code', async () => {
  const app = build();
  const res = await app.inject({ method: 'POST', url: '/render-code', payload: {} });
  assert.equal(res.statusCode, 400);
});

test('render-code returns 500 when the runner fails', async () => {
  const failing: Renderer = {
    run: async () => {
      throw new Error('render boom');
    },
  };
  const app = build(failing);
  const res = await app.inject({
    method: 'POST',
    url: '/render-code',
    payload: { code: 'x' },
  });
  assert.equal(res.statusCode, 500);
  assert.match(res.json().error, /render boom/);
});
