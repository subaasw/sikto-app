import assert from 'node:assert';
import { test } from 'node:test';
import { getTemplate } from '../src/templates/registry.ts';
import { speechPulse } from '../src/templates/marketing.tsx';
import type { Animation, Element, SceneTheme } from '../src/types.ts';

const MARKETING: SceneTheme = {
  primary: '#f97316',
  background: '#0c0a09',
  foreground: '#fff7ed',
  font: 'Geist',
  template: 'marketing',
  background_style: 'texture',
  element_style: 'sticker',
  motion: 'punchy',
};

const el: Element = { id: 'x', type: 'image', frame: { x: 0, y: 0, w: 0.5, h: 0.5 }, z: 0, src: '/a.png' };
const anim: Animation = { target_id: 'x', type: 'fade-in', at_ms: 0, duration_ms: 500 };

test('registry resolves marketing by id and by capability flags', () => {
  assert.equal(getTemplate(MARKETING).id, 'marketing');
  assert.equal(getTemplate({ ...MARKETING, template: undefined }).id, 'marketing'); // inferred
  assert.equal(
    getTemplate({ ...MARKETING, template: undefined, element_style: 'plain', background_style: 'gradient', motion: 'smooth' }).id,
    'explainer',
  );
});

test('marketing entrance is deterministic and finite', () => {
  const ctx = { element: el, anim, atMs: 0, progressMs: 250, index: 2, profile: 'video' as const };
  const a = getTemplate(MARKETING).entrance(ctx);
  const b = getTemplate(MARKETING).entrance(ctx);
  assert.deepEqual(a, b); // same inputs -> same output (player == MP4)
  assert.ok(typeof a.opacity === 'number' && Number.isFinite(a.opacity));
  assert.ok(typeof a.transform === 'string' && !a.transform.includes('NaN'));
});

test('speechPulse spikes at a word onset and is 0 with no words', () => {
  const words = [
    { text: 'buy', start_ms: 100, end_ms: 300 },
    { text: 'now', start_ms: 500, end_ms: 700 },
  ];
  assert.equal(speechPulse(undefined, 100), 0);
  assert.ok(speechPulse(words, 100) > 0.9); // right at onset
  assert.ok(speechPulse(words, 100) > speechPulse(words, 300)); // decays
  assert.equal(speechPulse(words, 50), 0); // before any word
});

test('marketing sticker treatment applies only when element_style=sticker', () => {
  const t = getTemplate(MARKETING).elementTreatment!(el, MARKETING);
  assert.equal(t.imageObjectFit, 'cover');
  assert.ok(t.wrapStyle);
  assert.deepEqual(getTemplate(MARKETING).elementTreatment!(el, { ...MARKETING, element_style: 'plain' }), {});
});
