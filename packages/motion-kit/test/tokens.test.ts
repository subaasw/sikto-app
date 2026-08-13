import assert from 'node:assert/strict';
import { test } from 'node:test';
import { DESIGN_H, DESIGN_W, PALETTES } from '../src/tokens';

test('every palette is complete and dark-canvas', () => {
  assert.equal(DESIGN_W / DESIGN_H, 16 / 9);
  for (const [name, p] of Object.entries(PALETTES)) {
    for (const key of ['bg', 'bg2', 'ink', 'soft', 'accent'] as const) {
      assert.match(p[key], /^#[0-9a-f]{6}$/i, `${name}.${key}`);
    }
    assert.equal(p.mesh.length, 4, `${name}.mesh`);
    // bg must be dark enough for light ink (relative luminance < 0.2)
    const [r, g, b] = [1, 3, 5].map((i) => parseInt(p.bg.slice(i, i + 2), 16) / 255);
    assert.ok(0.2126 * r + 0.7152 * g + 0.0722 * b < 0.2, `${name}.bg too light`);
  }
});
