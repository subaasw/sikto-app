import assert from 'node:assert';
import { test } from 'node:test';
import { getTemplate } from '../src/templates/registry.ts';
import { renderBackground } from '../src/templates/backgrounds.tsx';
import type { Animation, Element, SceneTheme } from '../src/types.ts';

const THEME: SceneTheme = {
  primary: '#34d399',
  background: '#0b0f0e',
  foreground: '#e9efe9',
  font: 'Geist',
  template: 'marketing',
  background_style: 'solid',
  element_style: 'sticker',
  motion: 'punchy',
};

const img: Element = { id: 'x', type: 'image', frame: { x: 0, y: 0, w: 0.5, h: 0.5 }, z: 0, src: '/a.png' };
const anim: Animation = { target_id: 'x', type: 'fade-in', at_ms: 0, duration_ms: 500 };
const words = [{ word: 'hi', start_ms: 100, end_ms: 300 }];

test('background is static — identical regardless of progressMs (no drift)', () => {
  // renderBackground ignores time now; if anyone reintroduces motion this fails.
  assert.deepEqual(renderBackground(THEME, 0), renderBackground(THEME, 9000));
});

test('marketing visual entrance settles — no continuous motion after it finishes', () => {
  const tpl = getTemplate(THEME);
  const at = (progressMs: number) =>
    tpl.entrance({ element: img, anim, atMs: 0, progressMs, index: 0, profile: 'video', words });
  // Two samples well past the 500ms entrance must be identical — i.e. no breath/pulse.
  assert.deepEqual(at(8000), at(16000));
});
