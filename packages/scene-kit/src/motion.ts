// Shared easing/progress helpers. Per-template entrance motion lives in
// templates/<name>.tsx; this file is just the math they build on.

export function clamp(v: number, lo: number, hi: number): number {
  return Math.max(lo, Math.min(hi, v));
}

/** Guarded 0..1 entrance progress for an element starting at `atMs`. */
export function linear(atMs: number, progressMs: number, durationMs: number): number {
  const ratio = (progressMs - atMs) / Math.max(1, durationMs);
  return Number.isFinite(ratio) ? clamp(ratio, 0, 1) : 1;
}

export function easeOut(t: number): number {
  return 1 - Math.pow(1 - t, 3);
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
