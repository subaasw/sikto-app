import assert from 'node:assert';
import { test } from 'node:test';
import { fitFontPx, fitFontCqw, STAGE_W } from '../src/fit.ts';

// Fake measurer: monospace-ish, width = chars * px * 0.55.
const fake = (text: string, px: number) => text.length * px * 0.55;

test('long text in a small box shrinks so wrapped height fits', () => {
  const box = { w: 400, h: 80 };
  const long = 'This is a very long heading that would never fit at a large size';
  const px = fitFontPx(long, box, { minPx: 8, maxPx: 200, lineHeight: 1.2 }, fake);
  const lines = Math.ceil(fake(long, px) / box.w);
  assert.ok(lines * px * 1.2 <= box.h + 0.5, `height ${lines * px * 1.2} should fit ${box.h}`);
  assert.ok(px >= 8 && px < 200);
});

test('short text in a big box is not shrunk below the cap', () => {
  const px = fitFontPx('Hi', { w: 1000, h: 400 }, { minPx: 8, maxPx: 120, lineHeight: 1.2 }, fake);
  assert.equal(px, 120);
});

test('longest word never exceeds box width', () => {
  const box = { w: 120, h: 600 };
  const px = fitFontPx('antidisestablishmentarianism', box, { minPx: 6, maxPx: 200, lineHeight: 1.2 }, fake);
  assert.ok(fake('antidisestablishmentarianism', px) <= box.w + 0.5);
});

test('empty / zero-box returns the floor', () => {
  assert.equal(fitFontPx('', { w: 100, h: 100 }, { minPx: 10, maxPx: 80, lineHeight: 1.2 }, fake), 10);
  assert.equal(fitFontPx('x', { w: 0, h: 100 }, { minPx: 10, maxPx: 80, lineHeight: 1.2 }, fake), 10);
});

test('cqw conversion is px relative to canonical stage width', () => {
  const cqw = fitFontCqw('Hi', { x: 0, y: 0, w: 1, h: 1 }, { minPx: 8, maxPx: 128, lineHeight: 1.2 }, fake);
  // fits at max 128px in a full-width/full-height box → 128/1280*100 = 10cqw
  assert.ok(Math.abs(cqw - (128 / STAGE_W) * 100) < 0.01);
});
