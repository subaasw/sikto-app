import assert from 'node:assert/strict';
import { test } from 'node:test';
import {
  contrastRatio,
  MIN_TEXT_CQW,
  resolveTokens,
  TEMPLATE_TOKENS,
  TYPE_SCALE,
  withAlpha,
} from '../src/tokens';
import type { SceneTheme } from '../src/types';

const themeOf = (over: Partial<SceneTheme>): SceneTheme => ({
  primary: '#2563eb',
  background: '#f6f7f9',
  foreground: '#1f2937',
  font: 'Geist',
  template: 'explainer',
  ...over,
});

test('every shipped palette meets the legibility floors', () => {
  for (const [name, t] of Object.entries(TEMPLATE_TOKENS)) {
    const p = t.palette;
    assert.ok(contrastRatio(p.ink, p.bg) >= 4.5, `${name}: ink/bg`);
    assert.ok(contrastRatio(p.soft, p.bg) >= 3.0, `${name}: soft/bg`);
    assert.ok(contrastRatio(p.accent, p.bg) >= 3.0, `${name}: accent/bg`);
    assert.ok(contrastRatio(p.accent2, p.bg) >= 3.0, `${name}: accent2/bg`);
    assert.ok(contrastRatio(p.accent_ink, p.accent) >= 3.0, `${name}: accent_ink/accent`);
    assert.ok(contrastRatio(p.ink, p.surface) >= 4.5, `${name}: ink/surface`);
  }
});

test('body and caption sizes meet the 40px@1080p floor', () => {
  assert.ok(TYPE_SCALE.body.size >= MIN_TEXT_CQW);
  assert.ok(TYPE_SCALE.caption.size >= MIN_TEXT_CQW);
  // titles ≥ 1.5× body (legibility.info)
  assert.ok(TYPE_SCALE.h1.size >= TYPE_SCALE.body.size * 1.5);
});

test('resolveTokens: template defaults when theme has no palette', () => {
  const t = resolveTokens(themeOf({ template: 'whiteboard', background: '#f8fafc', foreground: '#1e2937', primary: '#2456c9' }));
  assert.equal(t.palette.accent, '#2456c9');
  assert.equal(t.texture, 'grain');
  assert.match(t.fonts.script, /Caveat/);
});

test('resolveTokens: explicit palette wins over template', () => {
  const t = resolveTokens(themeOf({ palette: { bg: '#101315', ink: '#eef1f3' } }));
  assert.equal(t.palette.bg, '#101315');
  assert.equal(t.palette.ink, '#eef1f3');
  assert.equal(t.palette.accent, TEMPLATE_TOKENS.explainer.palette.accent); // unset roles inherit
});

test('resolveTokens: legacy director repaint folds into roles', () => {
  const t = resolveTokens(themeOf({ background: '#10151a', foreground: '#e8eef4', primary: '#59b0ff' }));
  assert.equal(t.palette.bg, '#10151a');
  assert.equal(t.palette.ink, '#e8eef4');
  assert.equal(t.palette.accent, '#59b0ff');
  assert.ok(contrastRatio(t.palette.ink, t.palette.bg) >= 4.5);
});

test('withAlpha renders rgba from short and long hex', () => {
  assert.equal(withAlpha('#ffffff', 0.5), 'rgba(255,255,255,0.5)');
  assert.equal(withAlpha('#fff', 1), 'rgba(255,255,255,1)');
});

test('contrastRatio matches known WCAG values', () => {
  assert.equal(Math.round(contrastRatio('#000000', '#ffffff')), 21);
  assert.equal(Math.round(contrastRatio('#ffffff', '#ffffff')), 1);
});
