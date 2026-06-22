import { clamp, easeOut, linear } from '../motion';
import type { TemplateModule } from './types';

/** Whiteboard — hand-drawn: quick fades (shapes draw themselves via the `draw`
 * animation + Rough.js strokes in ElementView). */
export const whiteboard: TemplateModule = {
  id: 'whiteboard',
  entrance: ({ anim, atMs, progressMs, profile }) => {
    if (anim.type === 'draw') return { opacity: 1 };
    const lin = linear(atMs, progressMs, anim.duration_ms);
    if (profile === 'slide') return { opacity: easeOut(lin) };
    return { opacity: clamp(lin * 1.6, 0, 1) };
  },
};
