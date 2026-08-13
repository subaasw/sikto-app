// Stop-motion prop wobble: a pose held for 1/WOBBLE_FPS s, then a new pose.
// Applied to individual props only — the camera stays smooth.
export const WOBBLE_FPS = 10;

/** Tiny deterministic string hash -> [0, 1). No Math.random(), ever. */
export function hash01(seed: string): number {
  let h = 2166136261;
  for (let i = 0; i < seed.length; i++) {
    h ^= seed.charCodeAt(i);
    h = Math.imul(h, 16777619);
  }
  return ((h >>> 0) % 100000) / 100000;
}

export function wobbleAt(tMs: number, seed: string): { dx: number; dy: number; rot: number } {
  const step = Math.floor(tMs / (1000 / WOBBLE_FPS));
  return {
    dx: (hash01(`${seed}:${step}:x`) - 0.5) * 2.4,
    dy: (hash01(`${seed}:${step}:y`) - 0.5) * 2.4,
    rot: (hash01(`${seed}:${step}:r`) - 0.5) * 0.8,
  };
}
