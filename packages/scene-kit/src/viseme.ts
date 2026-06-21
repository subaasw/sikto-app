import type { WordTiming } from './types';

/** A mouth shape: how open and how rounded, each 0..1. */
export type Viseme = { open: number; round: number };

const VOWELS = new Set(['a', 'e', 'i']);
const ROUND = new Set(['o', 'u', 'w']);
const CLOSED = new Set(['m', 'b', 'p']);
const TEETH = new Set(['f', 'v']);
const REST: Viseme = { open: 0.05, round: 0 };

function letterViseme(ch: string): Viseme {
  const c = ch.toLowerCase();
  if (CLOSED.has(c)) return { open: 0.06, round: 0 };
  if (ROUND.has(c)) return { open: 0.55, round: 0.9 };
  if (TEETH.has(c)) return { open: 0.2, round: 0 };
  if (VOWELS.has(c)) return { open: 0.95, round: 0 };
  if (c >= 'a' && c <= 'z') return { open: 0.42, round: 0.1 };
  return REST;
}

/** Is a word being spoken near `progressMs` (within `padMs`)? Used to drive
 * gesture energy so the figure animates while talking and rests when silent. */
export function isSpeaking(words: WordTiming[] | undefined, progressMs: number, padMs = 160): boolean {
  if (!words || words.length === 0) return false;
  return words.some((w) => w.start_ms - padMs <= progressMs && progressMs <= w.end_ms + padMs);
}

/**
 * Mouth shape at `progressMs`, derived from the narration's word timings: the
 * spoken word's letters are spread across its time span and mapped to a mouth
 * shape, so the figure "flaps" in sync with the real voice. Closed in the gaps
 * between words. Pure → identical in the player and the MP4.
 */
export function visemeAt(words: WordTiming[] | undefined, progressMs: number): Viseme {
  if (!words || words.length === 0) return { open: 0, round: 0 };
  const w = words.find((c) => progressMs >= c.start_ms && progressMs < c.end_ms);
  if (!w) return REST; // between words
  const letters = w.text.replace(/[^a-zA-Z]/g, '');
  if (!letters) return REST;
  const frac = (progressMs - w.start_ms) / Math.max(1, w.end_ms - w.start_ms);
  const idx = Math.min(letters.length - 1, Math.max(0, Math.floor(frac * letters.length)));
  return letterViseme(letters[idx]);
}
