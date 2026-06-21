// A tiny deterministic 2D Verlet solver. Pure: given the same inputs it returns
// the same trajectory, so the live player and the Remotion MP4 match exactly.
//
// The trick (see the spec): a physics sim is iterative, but Remotion renders
// frames out of order. So we simulate the WHOLE scene once at a fixed timestep
// and memoize the trajectory (caller's job); each frame just samples it.

export type Vec = { x: number; y: number };

export interface Point {
  x: number;
  y: number;
  px: number; // previous position (Verlet velocity is x - px)
  py: number;
  pinned: boolean;
}

/** A distance constraint (bone) between two point indices. */
export type Stick = readonly [a: number, b: number, len: number];

export type Pose = Vec[];

/** Extra per-point acceleration at time `tMs` (e.g. springs pulling a hand to a
 * gesture target). Reads current positions so it can act like a spring. */
export type DriveFn = (tMs: number, points: readonly Point[]) => Vec[];

export interface SimOpts {
  gravity?: number;
  damping?: number;
  iterations?: number;
  capMs?: number;
}

export const DT = 1000 / 60; // fixed timestep (ms)

export function pt(x: number, y: number, pinned = false): Point {
  return { x, y, px: x, py: y, pinned };
}

function stepOnce(
  points: Point[],
  sticks: readonly Stick[],
  accel: Vec[],
  gravity: number,
  damping: number,
  iterations: number,
): void {
  for (let i = 0; i < points.length; i++) {
    const p = points[i];
    if (p.pinned) continue;
    const vx = (p.x - p.px) * damping;
    const vy = (p.y - p.py) * damping;
    p.px = p.x;
    p.py = p.y;
    p.x += vx + accel[i].x;
    p.y += vy + accel[i].y + gravity;
  }
  for (let it = 0; it < iterations; it++) {
    for (const [a, b, len] of sticks) {
      const pa = points[a];
      const pb = points[b];
      let dx = pb.x - pa.x;
      let dy = pb.y - pa.y;
      const d = Math.hypot(dx, dy) || 1e-6;
      const diff = (len - d) / d;
      const wa = pa.pinned ? 0 : pb.pinned ? 1 : 0.5;
      const wb = pb.pinned ? 0 : pa.pinned ? 1 : 0.5;
      dx *= diff;
      dy *= diff;
      pa.x -= dx * wa;
      pa.y -= dy * wa;
      pb.x += dx * wb;
      pb.y += dy * wb;
    }
  }
}

const snapshot = (points: readonly Point[]): Pose => points.map((p) => ({ x: p.x, y: p.y }));

/** Run the whole scene once → a pose per timestep. Memoize the result by your
 * inputs; do NOT call this per frame. */
export function simulate(
  init: readonly Point[],
  sticks: readonly Stick[],
  drive: DriveFn,
  durationMs: number,
  opts: SimOpts = {},
): Pose[] {
  const gravity = opts.gravity ?? 0.18;
  const damping = opts.damping ?? 0.94;
  const iterations = opts.iterations ?? 4;
  const cap = opts.capMs ?? 30_000;
  const total = Math.min(Math.max(durationMs, DT), cap);
  const steps = Math.ceil(total / DT);
  const points: Point[] = init.map((p) => ({ ...p }));
  const traj: Pose[] = [snapshot(points)];
  for (let k = 1; k <= steps; k++) {
    stepOnce(points, sticks, drive(k * DT, points), gravity, damping, iterations);
    traj.push(snapshot(points));
  }
  return traj;
}

/** Sample the trajectory at `progressMs`, lerping between the two nearest steps.
 * Clamps past the end (the figure settles rather than looping). */
export function poseAt(traj: Pose[], progressMs: number): Pose {
  if (traj.length === 0) return [];
  const f = Math.max(0, progressMs) / DT;
  const i = Math.floor(f);
  if (i >= traj.length - 1) return traj[traj.length - 1];
  const t = f - i;
  const a = traj[i];
  const b = traj[i + 1];
  return a.map((pa, j) => ({ x: pa.x + (b[j].x - pa.x) * t, y: pa.y + (b[j].y - pa.y) * t }));
}
