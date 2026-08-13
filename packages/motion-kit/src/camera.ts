import type { MotionCamera } from '@sikto/scene-kit';

export interface CameraPose {
  x: number; // design px
  y: number;
  scale: number;
  rot: number; // degrees
}

export const DRIFT_PX = 36; // total pan across a scene
export const ZOOM_MAX = 1.12; // spec ceiling 1.15
const ZOOM_MIN = 1.02; // always overscan: drift/tilt must never reveal canvas edges

const clamp = (v: number, lo: number, hi: number) => Math.min(hi, Math.max(lo, v));
const smooth = (t: number) => t * t * (3 - 2 * t); // smoothstep ease-in-out

/** Closed-form camera pose at `tMs` — pure, deterministic, holds past the end. */
export function cameraAt(tMs: number, durationMs: number, cam: MotionCamera): CameraPose {
  const t = smooth(clamp(tMs / Math.max(1, durationMs), 0, 1));
  const dx = cam.drift === 'left' ? -DRIFT_PX : cam.drift === 'right' ? DRIFT_PX : 0;
  const dy = cam.drift === 'up' ? -DRIFT_PX : cam.drift === 'down' ? DRIFT_PX : 0;
  const z0 = cam.zoom === 'in' ? ZOOM_MIN : cam.zoom === 'out' ? ZOOM_MAX : 1.05;
  const z1 = cam.zoom === 'in' ? ZOOM_MAX : cam.zoom === 'out' ? ZOOM_MIN : 1.05;
  return {
    x: dx * t - dx / 2,
    y: dy * t - dy / 2,
    scale: z0 + (z1 - z0) * t,
    rot: clamp(cam.tilt_deg, -2, 2) * t,
  };
}
