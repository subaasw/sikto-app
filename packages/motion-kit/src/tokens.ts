import type { MotionPaletteName } from '@sikto/scene-kit';

// Palettes are the ONLY colors the marketing engine uses — the LLM picks a
// name, never a hex. Muted, dark, professional; accent carries the energy.
export type { MotionPaletteName };

export interface MotionPalette {
  bg: string; // canvas
  bg2: string; // secondary surface / grid ink
  ink: string; // titles
  soft: string; // supporting text
  accent: string; // chip, underline, cta
  mesh: [string, string, string, string]; // MeshGradientBg stops (muted)
}

export const DESIGN_W = 1280;
export const DESIGN_H = 720;

export const PALETTES: Record<MotionPaletteName, MotionPalette> = {
  midnight: { bg: '#0b1220', bg2: '#16233c', ink: '#eef2f8', soft: '#9fb0c8', accent: '#4ecdc4', mesh: ['#13233f', '#0b1220', '#1b3a5c', '#123043'] },
  sunset:   { bg: '#1a1012', bg2: '#2a181e', ink: '#fdf1e7', soft: '#d3a99a', accent: '#ff8a5c', mesh: ['#3a1c22', '#1a1012', '#4a2330', '#2c1418'] },
  forest:   { bg: '#0e1712', bg2: '#18291f', ink: '#ecf5ee', soft: '#a3c2ab', accent: '#7ddc8f', mesh: ['#16301f', '#0e1712', '#1e4029', '#12291c'] },
  royal:    { bg: '#120f1f', bg2: '#1f1936', ink: '#f0edfa', soft: '#aca3cf', accent: '#a78bfa', mesh: ['#241b47', '#120f1f', '#2f2260', '#1a1536'] },
  ember:    { bg: '#171112', bg2: '#26191b', ink: '#faeeea', soft: '#c9a29b', accent: '#f4b642', mesh: ['#33201d', '#171112', '#442a24', '#241a18'] },
  slate:    { bg: '#101315', bg2: '#1b2226', ink: '#eef1f3', soft: '#a2adb5', accent: '#6cb2f5', mesh: ['#1c2830', '#101315', '#233542', '#16222b'] },
};
