import { clamp, easeOut, linear, springEase } from '../motion';
import { gradientBg } from './backgrounds';
import type { TemplateModule } from './types';

/** Explainer — clean, cinematic: soft gradient bg, smooth springy reveals. */
export const explainer: TemplateModule = {
  id: 'explainer',
  Background: ({ theme, progressMs }) => gradientBg(theme, progressMs),
  entrance: ({ anim, atMs, progressMs, profile }) => {
    if (anim.type === 'draw') return { opacity: 1 };
    const lin = linear(atMs, progressMs, anim.duration_ms);
    if (profile === 'slide') return { opacity: easeOut(lin) };
    return { opacity: clamp(springEase(lin), 0, 1) }; // spring fade, no vertical slide
  },
};
