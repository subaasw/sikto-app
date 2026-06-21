import type { CSSProperties } from 'react';
import type { Animation, MotionStyle, RenderProfile } from './types';

export function clamp(v: number, lo: number, hi: number): number {
  return Math.max(lo, Math.min(hi, v));
}

/** Under-damped spring step response, settling to 1 with a slight overshoot —
 * a lively "pop & settle". Pure function of `t∈[0,1]`. */
export function springEase(t: number): number {
  if (t <= 0) return 0;
  if (t >= 1) return 1;
  const omega = 9;
  const zeta = 0.62;
  const wd = omega * Math.sqrt(1 - zeta * zeta);
  return (
    1 - Math.exp(-zeta * omega * t) * (Math.cos(wd * t) + ((zeta * omega) / wd) * Math.sin(wd * t))
  );
}

const easeOut = (t: number) => 1 - Math.pow(1 - t, 3);

/**
 * Opacity / transform for an entrance, varying by the template's `motion` and the
 * render `profile`:
 * - `slide` profile → restrained: a quick fade, no movement (study/pause).
 * - `punchy` (marketing) → a fast scale "pop" from 82%.
 * - `sketch` (whiteboard) → a quick fade (shapes draw themselves separately).
 * - `smooth` (explainer, default) → the springy rise.
 * Pure function of progress, so player and MP4 match. Guards a non-finite `ms`.
 */
export function appearance(
  anim: Animation,
  atMs: number,
  ms: number,
  motion: MotionStyle,
  profile: RenderProfile,
): CSSProperties {
  const ratio = (ms - atMs) / Math.max(1, anim.duration_ms);
  const lin = Number.isFinite(ratio) ? clamp(ratio, 0, 1) : 1;

  if (profile === 'slide') {
    return { opacity: easeOut(lin) };
  }
  if (motion === 'punchy') {
    const t = easeOut(lin);
    return { opacity: clamp(lin * 1.5, 0, 1), transform: `scale(${(0.82 + 0.18 * t).toFixed(3)})` };
  }
  if (motion === 'sketch') {
    return { opacity: clamp(lin * 1.6, 0, 1) };
  }
  const s = springEase(lin);
  const opacity = clamp(s, 0, 1);
  if (anim.type === 'reveal') return { opacity, transform: `translateY(${(1 - s) * 28}px)` };
  return { opacity };
}
