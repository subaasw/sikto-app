import assert from 'node:assert';
import { test } from 'node:test';
import { visemeAt } from '../src/viseme.ts';

const word = (text: string, start_ms: number, end_ms: number) => ({ text, start_ms, end_ms });

test('vowel-heavy word opens the mouth', () => {
  assert.ok(visemeAt([word('aaaa', 0, 1000)], 500).open > 0.8);
});

test('closed consonant keeps the mouth nearly shut', () => {
  assert.ok(visemeAt([word('mmmm', 0, 1000)], 500).open < 0.2);
});

test('rounded letter rounds the mouth', () => {
  assert.ok(visemeAt([word('oooo', 0, 1000)], 500).round > 0.7);
});

test('between words the mouth is at rest', () => {
  const v = visemeAt([word('hi', 0, 100)], 500); // 500ms is past the only word
  assert.ok(v.open < 0.1);
});

test('no words → fully closed', () => {
  const v = visemeAt([], 100);
  assert.equal(v.open, 0);
  assert.equal(v.round, 0);
});
