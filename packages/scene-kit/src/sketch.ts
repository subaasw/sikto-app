import rough from 'roughjs';

// One shared generator. Rough.js's generator is pure (no DOM): it returns SVG
// path data, so it works identically in the browser and Remotion's headless
// Chrome. Seeded per shape → deterministic, so the player and the MP4 match.
const gen = rough.generator();

export type SketchPath = { d: string; stroke: string; strokeWidth: number; fill: string };

/** Stable small seed from an element id so the hand-drawn wobble is the same
 * every render (player == MP4). */
export function seedFromId(id: string): number {
  let h = 0;
  for (let i = 0; i < id.length; i++) h = (h * 31 + id.charCodeAt(i)) | 0;
  return Math.abs(h) % 100000;
}

function toPaths(drawable: ReturnType<typeof gen.rectangle>): SketchPath[] {
  return gen.toPaths(drawable).map((p) => ({
    d: p.d,
    stroke: p.stroke,
    strokeWidth: p.strokeWidth,
    fill: p.fill ?? 'none',
  }));
}

type Opts = { seed: number; stroke: string; strokeWidth?: number; roughness?: number };

/** Hand-drawn rectangle border in a `w×h` box (a couple px inset so the wobble
 * stays inside the frame). */
export function sketchRect(w: number, h: number, opts: Opts): SketchPath[] {
  return toPaths(
    gen.rectangle(3, 3, Math.max(1, w - 6), Math.max(1, h - 6), {
      seed: opts.seed,
      roughness: opts.roughness ?? 1.6,
      bowing: 1.2,
      stroke: opts.stroke,
      strokeWidth: opts.strokeWidth ?? 2.5,
      fill: 'none',
    }),
  );
}

/** Hand-drawn line between two points. */
export function sketchLine(
  x1: number,
  y1: number,
  x2: number,
  y2: number,
  opts: Opts,
): SketchPath[] {
  return toPaths(
    gen.line(x1, y1, x2, y2, {
      seed: opts.seed,
      roughness: opts.roughness ?? 1.5,
      bowing: 1.5,
      stroke: opts.stroke,
      strokeWidth: opts.strokeWidth ?? 2.5,
    }),
  );
}
