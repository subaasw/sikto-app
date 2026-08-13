import type { CSSProperties, ReactNode } from 'react';
import { useCurrentFrame, useVideoConfig } from 'remotion';
import { wobbleAt } from './wobble';

/** Stop-motion feel for ONE prop: a held micro-offset that re-poses ~10x/s. */
export function StepWobble({ seed, style, children }: { seed: string; style?: CSSProperties; children: ReactNode }) {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const w = wobbleAt((frame / fps) * 1000, seed);
  return (
    <div style={{ ...style, transform: `translate(${w.dx}px, ${w.dy}px) rotate(${w.rot}deg)` }}>
      {children}
    </div>
  );
}
