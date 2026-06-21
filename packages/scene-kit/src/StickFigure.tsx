import { useMemo } from 'react';
import { poseAt, pt, simulate, type DriveFn, type Point, type Stick, type Vec } from './physics';
import type { SceneTheme, WordTiming } from './types';
import { isSpeaking, visemeAt } from './viseme';

// Per-emotion face/posture preset.
const EXPR: Record<string, { browY: number; smile: number; energy: number }> = {
  neutral: { browY: 0, smile: 0.12, energy: 1 },
  excited: { browY: -2, smile: 0.9, energy: 1.7 },
  calm: { browY: 0.4, smile: 0.35, energy: 0.7 },
  curious: { browY: -1.2, smile: 0.2, energy: 1.15 },
  serious: { browY: 1.2, smile: -0.2, energy: 0.85 },
};

// Skeleton joints (indices) in a 0..100 x 0..175 space.
const H = 0, NECK = 1, SH = 2, LE = 3, LH = 4, RE = 5, RH = 6, HIP = 7, LK = 8, LF = 9, RK = 10, RF = 11;
const REST: Vec[] = [
  { x: 50, y: 32 }, // head
  { x: 50, y: 52 }, // neck
  { x: 50, y: 60 }, // shoulder
  { x: 38, y: 80 }, // L elbow
  { x: 30, y: 98 }, // L hand
  { x: 62, y: 80 }, // R elbow
  { x: 70, y: 98 }, // R hand
  { x: 50, y: 112 }, // hip
  { x: 44, y: 134 }, // L knee
  { x: 40, y: 156 }, // L foot (pinned)
  { x: 56, y: 134 }, // R knee
  { x: 60, y: 156 }, // R foot (pinned)
];
const PINNED = new Set([LF, RF]);
const dist = (a: Vec, b: Vec) => Math.hypot(a.x - b.x, a.y - b.y);
const BONES: [number, number][] = [
  [H, NECK], [NECK, SH], [SH, LE], [LE, LH], [SH, RE], [RE, RH],
  [SH, HIP], [HIP, LK], [LK, LF], [HIP, RK], [RK, RF],
];
const STICKS: Stick[] = BONES.map(([a, b]) => [a, b, dist(REST[a], REST[b])] as Stick);
const initPoints = (): Point[] => REST.map((p, i) => pt(p.x, p.y, PINNED.has(i)));

// Spring stiffness per joint (0 = free, follows the bones — e.g. elbows bend).
const K: Record<number, number> = {
  [H]: 0.02, [SH]: 0.07, [HIP]: 0.07, [LK]: 0.05, [RK]: 0.05, [LH]: 0.035, [RH]: 0.035,
};

function makeDrive(words: WordTiming[] | undefined, energy: number): DriveFn {
  return (t, pts) => {
    const sway = Math.sin(t / 950) * 2.4 * energy; // weight shift
    const speak = isSpeaking(words, t) ? 1 : 0;
    const targets: Record<number, Vec> = {
      [HIP]: { x: 50 + sway, y: 112 },
      [SH]: { x: 50 + sway * 0.7, y: 60 },
      [H]: { x: 50 + sway * 0.5, y: 32 },
      [LK]: { x: 44 + sway * 0.5, y: 134 },
      [RK]: { x: 56 + sway * 0.5, y: 134 },
      [LH]: { x: 30 + Math.sin(t / 620) * 1.5 * energy, y: 98 },
      // the right hand gestures up toward the content while speaking
      [RH]: speak ? { x: 80, y: 70 } : { x: 70 + Math.sin(t / 680) * 1.5, y: 98 },
    };
    return pts.map((p, i) => {
      const target = targets[i];
      const k = K[i];
      if (!target || !k) return { x: 0, y: 0 };
      return { x: (target.x - p.x) * k, y: (target.y - p.y) * k };
    });
  };
}

/**
 * A procedural stick-figure presenter driven by a deterministic Verlet solver
 * (see physics.ts): jointed arms that bend at the elbow with momentum, a
 * weight-shifting torso, and a head that settles with overshoot. The trajectory
 * is simulated once (memoized) and sampled by `progressMs` → identical in the
 * player and the MP4. Lip-sync (`visemeAt`) and blink are layered on top.
 */
export function StickFigure({
  progressMs,
  durationMs,
  words,
  emotion = 'neutral',
  theme,
}: {
  progressMs: number;
  durationMs?: number;
  words?: WordTiming[];
  emotion?: string;
  theme: SceneTheme;
}) {
  const e = EXPR[emotion] ?? EXPR.neutral;
  const t = Number.isFinite(progressMs) ? progressMs : 0;
  const dur = durationMs && durationMs > 0 ? durationMs : 6000;
  const last = words && words.length ? words[words.length - 1].end_ms : 0;
  const trajectory = useMemo(
    () =>
      simulate(initPoints(), STICKS, makeDrive(words, e.energy), dur, {
        gravity: 0.1,
        damping: 0.9,
        iterations: 6,
      }),
    // wordsKey + energy + dur fully determine the sim.
    [words?.length, last, e.energy, dur], // eslint-disable-line react-hooks/exhaustive-deps
  );
  const pose = poseAt(trajectory, t);

  const head = pose[H];
  const neck = pose[NECK];
  // Head tilt = lean of the neck→head bone (gives a lively, physical head).
  const tilt = (Math.atan2(head.x - neck.x, neck.y - head.y) * 180) / Math.PI;
  const blink = ((t % 3200) + 3200) % 3200 < 130;
  const eyeRy = blink ? 0.5 : 2.3;
  const { open, round } = visemeAt(words, t);
  const stroke = theme.primary;

  return (
    <svg viewBox="0 0 100 175" preserveAspectRatio="xMidYMid meet" style={{ width: '100%', height: '100%' }}>
      <g stroke={stroke} strokeWidth={3.2} strokeLinecap="round" fill="none">
        {BONES.map(([a, b], i) => (
          <line key={i} x1={pose[a].x} y1={pose[a].y} x2={pose[b].x} y2={pose[b].y} />
        ))}
        <circle cx={head.x} cy={head.y} r={18} fill={theme.background} />
      </g>
      <g transform={`rotate(${tilt.toFixed(2)} ${head.x.toFixed(2)} ${head.y.toFixed(2)})`}>
        <g stroke={stroke} strokeWidth={2.6} strokeLinecap="round">
          <line x1={head.x - 9} y1={head.y - 6 + e.browY} x2={head.x - 3} y2={head.y - 7 + e.browY} />
          <line x1={head.x + 3} y1={head.y - 7 + e.browY} x2={head.x + 9} y2={head.y - 6 + e.browY} />
        </g>
        <g fill={stroke} stroke="none">
          <ellipse cx={head.x - 6} cy={head.y - 1} rx={2} ry={eyeRy} />
          <ellipse cx={head.x + 6} cy={head.y - 1} rx={2} ry={eyeRy} />
          <ellipse cx={head.x} cy={head.y + 8 - e.smile * 2} rx={6 - round * 2.5} ry={1.2 + open * 6} />
        </g>
      </g>
      <g fill={stroke} stroke="none">
        <circle cx={pose[LH].x} cy={pose[LH].y} r={2.3} />
        <circle cx={pose[RH].x} cy={pose[RH].y} r={2.3} />
      </g>
    </svg>
  );
}
