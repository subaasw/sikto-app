import type { MotionPalette } from './tokens';
import { DESIGN_H, DESIGN_W } from './tokens';
import { StepWobble } from './StepWobble';
import { hash01 } from './wobble';

/** Deterministic torn-paper edge: a strip whose top is a jittered polyline. */
export function tornEdge(seed: string, points = 16): string {
  const pts = ['0% 100%'];
  for (let i = 0; i <= points; i++) {
    const x = (i / points) * 100;
    const y = 2 + hash01(`${seed}:${i}`) * 9;
    pts.push(`${x.toFixed(1)}% ${y.toFixed(1)}%`);
  }
  pts.push('100% 100%');
  return `polygon(${pts.join(', ')})`;
}

const GRAIN = `url("data:image/svg+xml,${encodeURIComponent(
  '<svg xmlns="http://www.w3.org/2000/svg" width="180" height="180"><filter id="g"><feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves="2"/></filter><rect width="180" height="180" filter="url(#g)"/></svg>',
)}")`;

/** Construction-paper collage on the dark canvas: torn strips layered at the
 * bottom, cutout "sticker" shapes with hard offset shadows, paper grain on
 * top. Everything re-poses via StepWobble for the stop-motion paper feel. */
export function PaperBg({ palette, seed }: { palette: MotionPalette; seed: string }) {
  const strips = [
    { color: palette.mesh[2], top: 66 },
    { color: palette.bg2, top: 80 },
  ];
  const stickers = [0, 1, 2, 3].map((i) => {
    const k = `${seed}:paper:${i}`;
    const size = 70 + hash01(`${k}:s`) * 120;
    const x = hash01(`${k}:x`) * (DESIGN_W - size);
    const yRaw = hash01(`${k}:y`) * (DESIGN_H - size);
    // keep stickers out of the middle band where the text column lives
    const y = yRaw > DESIGN_H * 0.25 && yRaw < DESIGN_H * 0.55 ? yRaw + DESIGN_H * 0.3 : yRaw;
    return {
      size,
      x,
      y: Math.min(y, DESIGN_H - size - 24),
      round: hash01(`${k}:k`) > 0.5,
      rot: (hash01(`${k}:r`) - 0.5) * 14,
    };
  });
  return (
    <div style={{ position: 'absolute', inset: 0 }}>
      {strips.map((s, i) => (
        <StepWobble
          key={i}
          seed={`${seed}:strip:${i}`}
          style={{
            position: 'absolute',
            left: -24,
            right: -24,
            top: `${s.top}%`,
            bottom: -24,
            filter: 'drop-shadow(0 -6px 12px rgba(0,0,0,0.5))',
          }}
        >
          <div style={{ position: 'absolute', inset: 0, background: s.color, clipPath: tornEdge(`${seed}:strip:${i}`) }} />
        </StepWobble>
      ))}
      {stickers.map((s, i) => (
        <StepWobble key={`st${i}`} seed={`${seed}:sticker:${i}`} style={{ position: 'absolute', left: s.x, top: s.y }}>
          <div
            style={{
              width: s.size,
              height: s.round ? s.size : s.size * 0.32,
              borderRadius: s.round ? '50%' : 10,
              background: palette.accent,
              opacity: 0.16,
              transform: `rotate(${s.rot}deg)`,
              boxShadow: '5px 7px 0 rgba(0,0,0,0.35)',
            }}
          />
        </StepWobble>
      ))}
      <div style={{ position: 'absolute', inset: 0, backgroundImage: GRAIN, opacity: 0.06 }} />
    </div>
  );
}
