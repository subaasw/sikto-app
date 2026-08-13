// Hand-drawn marker strokes for the whiteboard, as plain SVG path data + a tiny
// component that "draws them on" via stroke-dashoffset. Pure and deterministic
// (a seed -> the same wobble every frame), so there's no per-frame shake and the
// browser preview is pixel-identical to the Remotion MP4. No DOM/canvas, so it
// renders fine under SSR. ponytail: hand-rolled wobble instead of wiring roughjs'
// generator — a few lines, fully under our control; swap in roughjs if we ever
// want richer hatching.

import { createElement, type CSSProperties } from 'react';

/** Seeded LCG -> a stable pseudo-random stream in [0,1). */
function rng(seed: number): () => number {
  let s = (seed | 0) || 1;
  return () => {
    s = (s * 1103515245 + 12345) & 0x7fffffff;
    return s / 0x7fffffff;
  };
}

/** Stable seed from a string so each mark wobbles the same way every render. */
export function seedFrom(str: string): number {
  let h = 2166136261;
  for (let i = 0; i < str.length; i++) {
    h ^= str.charCodeAt(i);
    h = Math.imul(h, 16777619);
  }
  return h & 0x7fffffff;
}

/** A roughly-horizontal underline across a 0..100 x 0..12 box, hand-wobbled. */
export function wobblyLine(seed: number, y = 6, amp = 1.8, segs = 12): string {
  const r = rng(seed);
  const pts: string[] = [];
  for (let i = 0; i <= segs; i++) {
    const x = 2 + (96 * i) / segs;
    const yy = y + (r() - 0.5) * 2 * amp + Math.sin(i * 0.9) * 0.4;
    pts.push(`${x.toFixed(1)},${yy.toFixed(1)}`);
  }
  return `M ${pts.join(' L ')}`;
}

/** A sketched rectangle outline over a 0..100 x 0..100 box (slightly open + wobbly,
 * like a marker box). Drawn as one continuous stroke so it draws on cleanly. */
export function wobblyRect(seed: number, amp = 1.6): string {
  const r = rng(seed);
  const j = () => (r() - 0.5) * 2 * amp;
  const a = 3 + r() * 2; // small overshoot at the start corner
  const x0 = 4, y0 = 4, x1 = 96, y1 = 96;
  return [
    `M ${x0 + j()} ${y0 + a}`,
    `L ${x0 + j()} ${y0 + j()} L ${x1 + j()} ${y0 + j()}`, // top
    `L ${x1 + j()} ${y1 + j()}`, // right
    `L ${x0 + j()} ${y1 + j()}`, // bottom
    `L ${x0 + j()} ${y0 + j()}`, // left, back to start
  ].join(' ');
}

/** Stroke a sketch path, revealing it left-to-right as `reveal` goes 0->1 — the
 * marker laying down ink. The reveal is a wipe mask on the whole SVG (robust:
 * stroke-dashoffset normalization fights `non-scaling-stroke`, which gave broken
 * dashes), so the stroke keeps an even width and simply appears as it's drawn. */
export function Sketch({
  d,
  reveal,
  color,
  width = 2.5,
  viewBox = '0 0 100 100',
  style,
}: {
  d: string;
  reveal: number;
  color: string;
  width?: number;
  viewBox?: string;
  style?: CSSProperties;
}) {
  const edge = Math.max(0, Math.min(1, reveal)) * 100;
  const mask =
    reveal >= 1
      ? undefined
      : `linear-gradient(to right, #000 ${Math.max(0, edge - 5).toFixed(2)}%, transparent ${edge.toFixed(2)}%)`;
  return createElement(
    'svg',
    {
      viewBox,
      preserveAspectRatio: 'none',
      'aria-hidden': true,
      style: {
        position: 'absolute',
        inset: 0,
        width: '100%',
        height: '100%',
        overflow: 'visible',
        pointerEvents: 'none',
        ...(mask ? { WebkitMaskImage: mask, maskImage: mask } : {}),
        ...style,
      },
    },
    createElement('path', {
      d,
      fill: 'none',
      stroke: color,
      strokeWidth: width,
      strokeLinecap: 'round',
      strokeLinejoin: 'round',
      vectorEffect: 'non-scaling-stroke',
    }),
  );
}
