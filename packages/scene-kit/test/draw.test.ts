import assert from 'node:assert/strict';
import { test } from 'node:test';
import { drawWindows, revealFor } from '../src/whiteboard';

test('windows are sequential and non-overlapping', () => {
  const w = drawWindows(3, 10000);
  assert.equal(w.length, 3);
  assert.equal(w[0].start, 0);
  for (let i = 0; i < w.length; i++) assert.ok(w[i].end > w[i].start);
  for (let i = 1; i < w.length; i++) assert.ok(w[i].start >= w[i - 1].end); // gap, no overlap
});

test('short scenes compress so the last draw lands within the scene', () => {
  const dur = 1500; // too short for 4 nominal windows
  const w = drawWindows(4, dur);
  assert.ok(w[w.length - 1].end <= dur, `last draw ${w[w.length - 1].end} should fit in ${dur}`);
});

test('revealFor clamps and rises monotonically through the window', () => {
  const win = { start: 1000, end: 2000 };
  assert.equal(revealFor(500, win), 0);
  assert.equal(revealFor(2500, win), 1);
  assert.ok(revealFor(1250, win) < revealFor(1750, win));
});

test('no drawable layers -> no windows', () => {
  assert.deepEqual(drawWindows(0, 4000), []);
});
