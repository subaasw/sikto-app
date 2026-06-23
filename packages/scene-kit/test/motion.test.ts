import assert from 'node:assert';
import { test } from 'node:test';
import { clamp, easeOut, linear, springEase } from '../src/motion.ts';

// Per-template entrance motion is tested in templates.test.ts; this file covers
// the shared easing/progress math those modules build on.

test('linear is guarded 0..1 progress from an element start time', () => {
  assert.equal(linear(0, 0, 500), 0);
  assert.equal(linear(0, 250, 500), 0.5);
  assert.equal(linear(0, 9999, 500), 1); // clamps
  assert.equal(linear(0, 100, 0), 1); // zero duration → finished, not NaN
});

test('easeOut and clamp behave', () => {
  assert.equal(easeOut(0), 0);
  assert.ok(Math.abs(easeOut(1) - 1) < 1e-9);
  assert.equal(clamp(5, 0, 1), 1);
});

test('springEase settles to ~1 and starts at 0', () => {
  assert.equal(springEase(0), 0);
  assert.ok(Math.abs(springEase(1) - 1) < 1e-6);
  // Calm settle: overshoot stays modest (zeta tuned up) so entrances don't wobble.
  const peak = Math.max(...Array.from({ length: 100 }, (_, i) => springEase(i / 99)));
  assert.ok(peak < 1.12, `overshoot too large: ${peak}`);
});
