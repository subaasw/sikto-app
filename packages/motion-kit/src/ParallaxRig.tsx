import type { MotionCamera, PlaneDepth } from '@sikto/scene-kit';
import type { ReactNode } from 'react';
import { cameraAt } from './camera';

export const DEPTH_MULT: Record<PlaneDepth, number> = { far: 0.35, mid: 0.65, near: 1 };

/**
 * Smooth camera over parallax planes. The rig scales/rotates as one unit
 * (the "camera"); each plane counter-translates by its depth multiplier so
 * far content moves less than near content. Planes overscan 6% so the pan
 * and tilt never reveal a canvas edge.
 */
export function ParallaxRig({
  camera,
  tMs,
  durationMs,
  layers,
  children,
}: {
  camera: MotionCamera;
  tMs: number;
  durationMs: number;
  layers: { depth: PlaneDepth; node: ReactNode }[];
  children: ReactNode; // foreground (depth 1): the text stack
}) {
  const pose = cameraAt(tMs, durationMs, camera);
  return (
    <div
      style={{
        position: 'absolute',
        inset: 0,
        transform: `scale(${pose.scale.toFixed(4)}) rotate(${pose.rot.toFixed(3)}deg)`,
        transformOrigin: '50% 50%',
      }}
    >
      {layers.map((l, i) => (
        <div
          key={i}
          style={{
            position: 'absolute',
            inset: '-6%',
            transform: `translate(${(-pose.x * DEPTH_MULT[l.depth]).toFixed(2)}px, ${(-pose.y * DEPTH_MULT[l.depth]).toFixed(2)}px)`,
          }}
        >
          {l.node}
        </div>
      ))}
      <div
        style={{
          position: 'absolute',
          inset: 0,
          transform: `translate(${(-pose.x).toFixed(2)}px, ${(-pose.y).toFixed(2)}px)`,
        }}
      >
        {children}
      </div>
    </div>
  );
}
