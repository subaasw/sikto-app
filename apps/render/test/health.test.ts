import assert from 'node:assert';
import { test } from 'node:test';
import { build } from '../src/server.ts';

test('health returns ok', async () => {
  const app = build();
  const res = await app.inject({ method: 'GET', url: '/health' });
  assert.equal(res.statusCode, 200);
  assert.equal(res.json().status, 'ok');
});

test('render stub returns an mp4 ref', async () => {
  const app = build();
  const res = await app.inject({ method: 'POST', url: '/render', payload: { plan: {} } });
  assert.equal(res.statusCode, 200);
  assert.match(res.json().video_ref, /\.mp4$/);
});
