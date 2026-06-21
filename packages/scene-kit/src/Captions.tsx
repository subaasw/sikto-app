import type { CSSProperties } from 'react';
import type { SceneTheme, WordTiming } from './types';

const MAX_WORDS = 6; // small cues that switch often, per caption UX

// Split into short cues, breaking at sentence ends so a cue never crosses one.
function chunkWords(words: WordTiming[]): number[][] {
  const out: number[][] = [];
  let cur: number[] = [];
  words.forEach((w, i) => {
    cur.push(i);
    const endsSentence = /[.!?]["')\]]?$/.test(w.text.trim());
    if (cur.length >= MAX_WORDS || endsSentence) {
      out.push(cur);
      cur = [];
    }
  });
  if (cur.length) out.push(cur);
  return out;
}

/**
 * Bottom caption synced to narration. Small, fixed-size cues that switch every few
 * words; words within a cue reveal as they're spoken (no color highlight, no
 * resize) so it reads consistently in both the live player and the Remotion render.
 * Driven by `progressMs`; renders nothing without word timings.
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
  // White text on a dark scrim reads on any theme; small + fixed so it never distracts.
  const scrim: CSSProperties = {
    maxWidth: '70%',
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
      <div style={scrim}>
        {chunk.map((wi) => (
          // Unspoken words keep their place (opacity 0) so the cue never resizes.
          <span key={wi} style={{ opacity: wi <= spoken ? 1 : 0 }}>
            {words[wi].text}{' '}
          </span>
        ))}
      </div>
    </div>
  );
}
