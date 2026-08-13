import type { PlaneDepth } from '@sikto/scene-kit';
import type { MotionPalette } from './tokens';
import { DESIGN_H, DESIGN_W } from './tokens';
import { hash01 } from './wobble';

/** 3 soft shapes per plane (ring / disc / rounded bar), placed by seed hash.
 * Far shapes are bigger and dimmer; near shapes smaller and slightly brighter. */
export function AbstractShapes({ palette, seed, depth }: { palette: MotionPalette; seed: string; depth: PlaneDepth }) {
  const dim = depth === 'far' ? 0.1 : depth === 'mid' ? 0.14 : 0.18;
  const base = depth === 'far' ? 300 : depth === 'mid' ? 180 : 110;
  const shapes = [0, 1, 2].map((i) => {
    const k = `${seed}:${depth}:${i}`;
    const size = base * (0.7 + hash01(`${k}:s`) * 0.6);
    // keep shapes out of the middle band where the text column lives
    const x = hash01(`${k}:x`) * (DESIGN_W - size);
    const yRaw = hash01(`${k}:y`) * (DESIGN_H - size);
    const y = yRaw > DESIGN_H * 0.25 && yRaw < DESIGN_H * 0.55 ? yRaw + DESIGN_H * 0.3 : yRaw;
    const kind = Math.floor(hash01(`${k}:k`) * 3);
    return { size, x, y: Math.min(y, DESIGN_H - size), kind };
  });
  return (
    <>
      {shapes.map((s, i) => (
        <div
          key={i}
          style={{
            position: 'absolute',
            left: s.x,
            top: s.y,
            width: s.size,
            height: s.kind === 2 ? s.size * 0.28 : s.size,
            borderRadius: s.kind === 2 ? s.size : '50%',
            border: s.kind === 0 ? `${Math.max(2, s.size * 0.06)}px solid ${palette.accent}` : 'none',
            background: s.kind === 0 ? 'transparent' : palette.accent,
            opacity: dim,
          }}
        />
      ))}
    </>
  );
}
