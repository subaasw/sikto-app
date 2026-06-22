import type { CSSProperties } from 'react';
import type { SceneTheme, WordTiming } from './types';

const MAX_CHARS = 42; // one readable line; cues swap when this fills or a sentence ends

// Split words into single-line cues of roughly equal length, never crossing a sentence.
function chunkWords(words: WordTiming[]): number[][] {
  const out: number[][] = [];
  let cur: number[] = [];
  let len = 0;
  words.forEach((w, i) => {
    const wlen = w.text.trim().length + 1;
    if (cur.length && len + wlen > MAX_CHARS) {
      out.push(cur);
      cur = [];
      len = 0;
    }
    cur.push(i);
    len += wlen;
    if (/[.!?]["')\]]?$/.test(w.text.trim())) {
      out.push(cur);
      cur = [];
      len = 0;
    }
  });
  if (cur.length) out.push(cur);
  return out;
}

/**
 * Bottom caption synced to narration. Shows one short line at a time and swaps to
 * the next line as narration advances — no word-by-word reveal, never wraps past a
 * single line. Driven by `progressMs`; renders nothing without word timings.
 */
export function Captions({
  words,
  progressMs,
}: {
  words: WordTiming[] | undefined;
  progressMs: number;
  theme: SceneTheme; // accepted for call-site compatibility; intentionally unused
}) {
  if (!words || words.length === 0) return null;

  // Index of the most recently started word (-1 before anything is spoken).
  let spoken = -1;
  for (let i = 0; i < words.length; i++) {
    if (words[i].start_ms <= progressMs) spoken = i;
    else break;
  }
  if (spoken === -1) return null;

  const chunks = chunkWords(words);
  const chunk = chunks.find((c) => c.includes(spoken)) ?? chunks[0] ?? [];
  const line = chunk.map((wi) => words[wi].text).join(' ');

  const container: CSSProperties = {
    position: 'absolute',
    inset: 0,
    containerType: 'inline-size',
    display: 'flex',
    alignItems: 'flex-end',
    justifyContent: 'center',
    pointerEvents: 'none',
    padding: '0 6% 5%',
  };
  // White text on a dark scrim reads on any theme; small, single-line, fixed.
  const scrim: CSSProperties = {
    maxWidth: '90%',
    whiteSpace: 'nowrap',
    textAlign: 'center',
    fontSize: '2.1cqw',
    lineHeight: 1.3,
    fontWeight: 600,
    color: '#ffffff',
    background: 'rgba(0,0,0,0.7)',
    padding: '0.5cqw 1.1cqw',
    borderRadius: '0.6cqw',
    textShadow: '0 0.1cqw 0.3cqw rgba(0,0,0,0.85)',
  };

  return (
    <div style={container}>
      <div style={scrim}>{line}</div>
    </div>
  );
}
