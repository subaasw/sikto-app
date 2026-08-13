import assert from 'node:assert/strict';
import { test } from 'node:test';
import { tornEdge } from '../src/PaperBg';

test('tornEdge is a deterministic closed polygon inside the box', () => {
  const a = tornEdge('s1');
  assert.equal(a, tornEdge('s1'));
  assert.notEqual(a, tornEdge('s2'));
  assert.match(a, /^polygon\(0% 100%, .+, 100% 100%\)$/);
  for (const [, x, y] of a.matchAll(/([\d.]+)% ([\d.]+)%/g)) {
    assert.ok(Number(x) >= 0 && Number(x) <= 100, `x ${x}`);
    assert.ok(Number(y) >= 0 && Number(y) <= 100, `y ${y}`);
  }
});
