import assert from 'node:assert';
import { test } from 'node:test';
import { seedFromId, sketchLine, sketchRect } from '../src/sketch.ts';

test('seedFromId is stable and deterministic', () => {
  assert.equal(seedFromId('s0-c1'), seedFromId('s0-c1'));
  assert.notEqual(seedFromId('s0-c1'), seedFromId('s0-c2'));
});

test('same seed yields identical rough paths (player == MP4)', () => {
  const a = sketchRect(200, 120, { seed: 42, stroke: '#000' });
  const b = sketchRect(200, 120, { seed: 42, stroke: '#000' });
  assert.deepEqual(a.map((p) => p.d), b.map((p) => p.d));
  assert.ok(a.length >= 1 && a[0].d.length > 0);
});

test('different seeds yield different strokes', () => {
  const a = sketchRect(200, 120, { seed: 1, stroke: '#000' });
  const b = sketchRect(200, 120, { seed: 2, stroke: '#000' });
  assert.notDeepEqual(a.map((p) => p.d), b.map((p) => p.d));
});

test('sketchLine produces a stroke path', () => {
  const paths = sketchLine(0, 0, 100, 0, { seed: 7, stroke: '#84cc16' });
  assert.ok(paths.length >= 1 && paths[0].d.includes('M'));
});
