import type { CSSProperties } from 'react';
import { clamp, easeOut, linear, springEase } from '../motion';
import { seedFromId } from '../sketch';
import type { Element, SceneTheme, WordTiming } from '../types';
import { textureBg } from './backgrounds';
import type { ElementTreatment, EntranceCtx, TemplateModule } from './types';

const STICKER_TYPES = new Set<Element['type']>(['image', 'card', 'shape', 'character']);

// A 0..1 "the voice just spoke" pulse: spikes at each word onset, decays over
// ~220ms. Lets every marketing element breathe in time with the narration.
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

// Playful entrance variants, chosen per element by reveal order so a scene
// never feels uniform. Each returns a transform that settles to identity.
const VARIANTS: ((lin: number) => string)[] = [
  (l) => `scale(${(0.8 + 0.2 * easeOut(l)).toFixed(3)})`, // pop
  (l) => `scale(${(0.6 + 0.4 * springEase(l)).toFixed(3)})`, // bounce (overshoot + settle)
  (l) => `translateX(${(Math.sin(l * Math.PI * 6) * (1 - l) * 9).toFixed(2)}px)`, // shake-in
  (l) => `rotate(${(Math.sin(l * Math.PI * 5) * (1 - l) * 7).toFixed(2)}deg)`, // wiggle-in
];

/** Always-on wobble for sticker elements, amplified while the voice speaks. */
function wobble(element: Element, progressMs: number, pulse: number): string {
  if (!STICKER_TYPES.has(element.type)) return '';
  const phase = ((seedFromId(element.id) % 100) / 100) * Math.PI * 2;
  const a = (Number.isFinite(progressMs) ? progressMs : 0) / 1400;
  const amp = 0.6 + pulse * 1.6;
  const rot = Math.sin(a + phase) * amp;
  const ty = Math.cos(a * 0.9 + phase) * amp * 0.5;
  return `rotate(${rot.toFixed(2)}deg) translateY(${ty.toFixed(2)}px)`;
}

/** Marketing — bold reel: grungy texture bg, sticker cut-outs, punchy varied
 * motion (pop/bounce/shake/wiggle) plus a continuous sticker wobble. */
export const marketing: TemplateModule = {
  id: 'marketing',
  Background: ({ theme, progressMs }) => textureBg(theme, progressMs),
  entrance: ({ element, anim, atMs, progressMs, index, profile, words }: EntranceCtx): CSSProperties => {
    if (anim.type === 'draw') return { opacity: 1 };
    const lin = linear(atMs, progressMs, anim.duration_ms);
    if (profile === 'slide') return { opacity: easeOut(lin) };

    // Text: one clean, confident pop-in (scale + spring settle). No shake or
    // wobble — headlines must stay readable.
    if (!STICKER_TYPES.has(element.type)) {
      const s = springEase(lin);
      return { opacity: clamp(lin * 1.8, 0, 1), transform: `scale(${(0.86 + 0.14 * s).toFixed(3)})` };
    }

    // Stickers (image/shape): playful entrance + a wobble that lifts with the voice.
    const enter = VARIANTS[index % VARIANTS.length](lin);
    const wob = wobble(element, progressMs, speechPulse(words, progressMs));
    return { opacity: clamp(lin * 1.5, 0, 1), transform: `${enter} ${wob}`.trim() };
  },
  elementTreatment: (element: Element, theme: SceneTheme): ElementTreatment => {
    if (theme.element_style !== 'sticker' || !STICKER_TYPES.has(element.type)) return {};
    return {
      imageObjectFit: 'cover',
      wrapStyle: {
        border: '0.55cqw solid #ffffff',
        borderRadius: '0.9cqw',
        boxShadow: '0 0.8cqw 1.8cqw rgba(0,0,0,0.38)',
        overflow: 'hidden',
        background: theme.background,
      },
    };
  },
};
