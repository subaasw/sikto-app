import type { Frame } from './types';

/** Canonical layout space: fits are computed here, then expressed in cqw so they
 * scale to any real display size and stay identical in player and render. */
export const STAGE_W = 1280;
export const STAGE_H = 720;

export type FitBox = { w: number; h: number }; // px in canonical space
export type Measure = (text: string, fontPx: number) => number; // single-line width (px)
export type FitOpts = { minPx?: number; maxPx?: number; lineHeight?: number };

/** Largest font (px) whose wrapped height ≤ box.h and whose longest word ≤ box.w. */
export function fitFontPx(text: string, box: FitBox, opts: FitOpts, measure: Measure): number {
  const min = opts.minPx ?? 8;
  const max = opts.maxPx ?? 200;
  const lh = opts.lineHeight ?? 1.2;
  const t = (text ?? '').trim();
  if (!t || box.w <= 0 || box.h <= 0) return min;

  const words = t.split(/\s+/);
  const fits = (px: number): boolean => {
    for (const w of words) if (measure(w, px) > box.w) return false;
    const lines = Math.max(1, Math.ceil(measure(t, px) / box.w));
    return lines * px * lh <= box.h;
  };

  if (fits(max)) return max;
  let lo = min;
  let hi = max;
  while (hi - lo > 0.5) {
    const mid = (lo + hi) / 2;
    if (fits(mid)) lo = mid;
    else hi = mid;
  }
  return Math.max(min, lo);
}

/** Fit text to a fractional `Frame`, returning a font size in cqw. */
export function fitFontCqw(text: string, frame: Frame, opts: FitOpts, measure: Measure): number {
  const box = { w: frame.w * STAGE_W, h: frame.h * STAGE_H };
  return (fitFontPx(text, box, opts, measure) / STAGE_W) * 100;
}

let _ctx: CanvasRenderingContext2D | null = null;

/** A `Measure` backed by the canvas text-metrics API. Identical in the browser
 * and Remotion's headless Chrome — no Remotion dependency, no DOM layout pass.
 * Falls back to a rough estimate when no canvas exists (SSR/Node). */
export function canvasMeasure(fontFamily: string, fontWeight: number | string = 400): Measure {
  return (text: string, fontPx: number): number => {
    if (typeof document === 'undefined') return text.length * fontPx * 0.55;
    _ctx ??= document.createElement('canvas').getContext('2d');
    if (!_ctx) return text.length * fontPx * 0.55;
    _ctx.font = `${fontWeight} ${fontPx}px ${fontFamily}`;
    return _ctx.measureText(text).width;
  };
}
