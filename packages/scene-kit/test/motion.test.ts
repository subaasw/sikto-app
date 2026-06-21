import assert from 'node:assert';
import { test } from 'node:test';
import { appearance, springEase } from '../src/motion.ts';

const anim = { target_id: 'x', type: 'reveal' as const, at_ms: 0, duration_ms: 500 };
const mid = 250; // halfway through the entrance

test('slide profile is restrained: a fade, no transform', () => {
  const s = appearance(anim, 0, mid, 'smooth', 'slide');
  assert.ok((s.opacity as number) > 0 && (s.opacity as number) < 1);
  assert.equal(s.transform, undefined);
});

test('punchy (marketing) pops with a scale transform', () => {
  const s = appearance(anim, 0, mid, 'punchy', 'video');
  assert.ok(typeof s.transform === 'string' && s.transform.startsWith('scale('));
});

test('smooth (explainer) reveal rises (translateY)', () => {
  const s = appearance(anim, 0, mid, 'smooth', 'video');
  assert.ok(typeof s.transform === 'string' && s.transform.includes('translateY'));
});

test('sketch (whiteboard) is a plain fade', () => {
  const s = appearance(anim, 0, mid, 'sketch', 'video');
  assert.equal(s.transform, undefined);
  assert.ok((s.opacity as number) > 0);
});

test('springEase settles to ~1 and starts at 0', () => {
  assert.equal(springEase(0), 0);
  assert.ok(Math.abs(springEase(1) - 1) < 1e-6);
});
