import assert from 'node:assert';
import { test } from 'node:test';
import type { SceneDocument } from '../src/remotion/schema.ts';
import { build } from '../src/server.ts';
import type { SceneRenderer } from '../src/sandbox/scene-runner.ts';
import { RemotionRunner } from '../src/sandbox/remotion-runner.ts';

const DOC: SceneDocument = {
  version: 1,
  title: 'Cells',
  summary: 'The unit of life',
  aspect_ratio: '16:9',
  theme: { primary: '#84cc16', background: '#0c0e08', foreground: '#edf2e2', font: 'Geist' },
  scenes: [
    {
      id: 's0',
      kind: 'slide',
      narration: { text: 'A cell is the smallest unit of life.' },
      elements: [
        { id: 's0-h', type: 'heading', frame: { x: 0.08, y: 0.12, w: 0.84, h: 0.16 }, z: 0, text: 'Cells' },
      ],
      animations: [{ target_id: 's0-h', type: 'fade-in', at_ms: 0, duration_ms: 400 }],
      manim_entry: 'MainScene',
    },
  ],
};

test('render-scene returns base64 video from the scene renderer', async () => {
  const fake: SceneRenderer = {
    render: async () => ({ video: Buffer.from('SCENEVID'), stdout: '', stderr: '' }),
  };
  const app = build(new RemotionRunner(), fake);
  const res = await app.inject({ method: 'POST', url: '/render-scene', payload: { document: DOC } });

  assert.equal(res.statusCode, 200);
  assert.equal(Buffer.from(res.json().video_b64, 'base64').toString(), 'SCENEVID');
});

test('render-scene requires a document', async () => {
  const app = build();
  const res = await app.inject({ method: 'POST', url: '/render-scene', payload: {} });
  assert.equal(res.statusCode, 400);
});

test('render-scene returns 500 when the renderer fails', async () => {
  const failing: SceneRenderer = {
    render: async () => {
      throw new Error('render boom');
    },
  };
  const app = build(new RemotionRunner(), failing);
  const res = await app.inject({ method: 'POST', url: '/render-scene', payload: { document: DOC } });
  assert.equal(res.statusCode, 500);
  assert.match(res.json().error, /render boom/);
});
