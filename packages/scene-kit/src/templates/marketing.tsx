import type { CSSProperties } from 'react';
import { clamp, easeOut, linear, springEase } from '../motion';
import type { Element, SceneTheme, WordTiming } from '../types';
import type { ElementTreatment, EntranceCtx, TemplateModule } from './types';

const STICKER_TYPES = new Set<Element['type']>(['image', 'card', 'shape', 'character']);

// 0..1 "the voice just spoke" pulse: spikes at each word onset, decays over
// ~220ms. Drives a subtle scale breath in time with the narration.
export function speechPulse(words: WordTiming[] | undefined, progressMs: number): number {
  if (!words || words.length === 0) return 0;
  const ms = Number.isFinite(progressMs) ? progressMs : 0;
  let pulse = 0;
  for (const w of words) {
    if (w.start_ms > ms) break;
    const dt = ms - w.start_ms;
    if (dt >= 0 && dt < 220) pulse = Math.max(pulse, 1 - dt / 220);
  }
  return pulse;
}

/** Marketing — bold reel: grungy texture bg + sticker cut-outs. Motion is a
 * clean scale-in; visuals get a subtle voice-synced breath — no shake, jitter,
 * or rotation. */
export const marketing: TemplateModule = {
  id: 'marketing',
  entrance: ({ element, anim, atMs, progressMs, profile, words }: EntranceCtx): CSSProperties => {
    if (anim.type === 'draw') return { opacity: 1 };
    const lin = linear(atMs, progressMs, anim.duration_ms);
    if (profile === 'slide') return { opacity: easeOut(lin) };
    const s = springEase(lin);

    // Text: confident pop-in, fully readable.
    if (!STICKER_TYPES.has(element.type)) {
      return { opacity: clamp(lin * 1.8, 0, 1), transform: `scale(${(0.86 + 0.14 * s).toFixed(3)})` };
    }

    // Visuals: clean scale-in + a gentle, smooth breath on the voice. No shake.
    const breath = 1 + 0.02 * speechPulse(words, progressMs);
    return {
      opacity: clamp(lin * 1.6, 0, 1),
      transform: `scale(${((0.9 + 0.1 * s) * breath).toFixed(3)})`,
    };
  },
  elementTreatment: (element: Element, theme: SceneTheme): ElementTreatment => {
    if (theme.element_style !== 'sticker' || !STICKER_TYPES.has(element.type)) return {};
    return {
      imageObjectFit: 'cover',
      wrapStyle: {
        border: '0.5cqw solid #ffffff',
        borderRadius: '0.9cqw',
        boxShadow: '0 0.8cqw 1.8cqw rgba(0,0,0,0.35)',
        overflow: 'hidden',
        background: theme.background,
      },
    };
  },
};
