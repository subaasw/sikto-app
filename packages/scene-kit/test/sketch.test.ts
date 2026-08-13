import assert from 'node:assert/strict';
import { test } from 'node:test';
import { seedFrom, wobblyLine, wobblyRect } from '../src/sketch';

test('seedFrom is deterministic and stable per string', () => {
  assert.equal(seedFrom('board-frame'), seedFrom('board-frame'));
  assert.notEqual(seedFrom('a'), seedFrom('b'));
});

test('wobble generators are deterministic and produce a valid SVG path', () => {
  const a = wobblyLine(42);
  const b = wobblyLine(42);
  assert.equal(a, b); // same seed -> same wobble (no per-frame shake)
  assert.notEqual(wobblyLine(42), wobblyLine(7));
  assert.match(a, /^M /);
  const rect = wobblyRect(seedFrom('x'));
  assert.match(rect, /^M /);
  assert.ok(rect.includes('L')); // a closed-ish outline of line segments
});
