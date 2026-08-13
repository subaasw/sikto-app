import type { MotionOutro } from '@sikto/scene-kit';
import type { CSSProperties, ReactNode } from 'react';

const OUTRO_MS = 500;
const smooth = (t: number) => t * t * (3 - 2 * t);

/** Scene exit in its own last 500ms: wipe / push / frosted. Keeps frame
 * continuity (no re-mounted Sequences) so entrances never replay. */
export function OutroWrap({
  outro,
  tMs,
  durationMs,
  children,
}: {
  outro: MotionOutro;
  tMs: number;
  durationMs: number;
  children: ReactNode;
}) {
  const p = Math.min(1, Math.max(0, (tMs - (durationMs - OUTRO_MS)) / OUTRO_MS));
  let style: CSSProperties = {};
  if (outro !== 'none' && p > 0) {
    const e = smooth(p);
    style =
      outro === 'wipe'
        ? { clipPath: `inset(0 ${(e * 100).toFixed(2)}% 0 0)` }
        : outro === 'push'
          ? { transform: `translateY(${(-e * 100).toFixed(2)}%)` }
          : { filter: `blur(${(e * 18).toFixed(1)}px)`, opacity: 1 - e };
  }
  return <div style={{ position: 'absolute', inset: 0, ...style }}>{children}</div>;
}
