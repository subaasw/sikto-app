import type { CSSProperties } from 'react';
import type { SceneTheme } from './types';
import { resolveTokens, textureStyle, withAlpha } from './tokens';
import { Sketch, seedFrom, wobblyRect } from './sketch';

// The board writes in a handwriting hand (Caveat) regardless of the theme font —
// a clean sans wiped on reads as a "transition"; handwriting wiped on reads as
// WRITING. Loaded by both hosts (web <link>, Remotion loadCaveat()).
// @deprecated read `resolveTokens(theme).fonts.script` instead.
export const WHITEBOARD_FONT = '"Caveat", "Comic Sans MS", cursive';

// --- draw-on timing ---------------------------------------------------------
// Whiteboard content is *drawn on* one layer at a time, in teaching order, then
// held. These pure helpers own the sequencing; SceneStage drives the wipe + hand
// from them. No per-frame randomness -> nothing "shakes".

export const DRAW_MS = 1100; // nominal time to draw one layer
export const GAP_MS = 180; // beat between layers

export interface DrawWindow {
  start: number;
  end: number;
}

/** Sequential draw windows for `count` layers, packed into the start of a scene.
 * Holds the last ~15% of the scene fully drawn; if the packed sequence overruns
 * the scene it scales down proportionally so the final draw still lands in time. */
export function drawWindows(count: number, sceneDurationMs: number): DrawWindow[] {
  if (count <= 0) return [];
  const nominal = count * DRAW_MS + (count - 1) * GAP_MS;
  const budget = Math.max(0, sceneDurationMs * 0.85);
  const scale = budget > 0 && nominal > budget ? budget / nominal : 1;
  const draw = DRAW_MS * scale;
  const gap = GAP_MS * scale;
  const out: DrawWindow[] = [];
  let t = 0;
  for (let i = 0; i < count; i++) {
    out.push({ start: t, end: t + draw });
    t += draw + gap;
  }
  return out;
}

/** Eased reveal fraction 0..1 for a layer at the scene clock `progressMs`. */
export function revealFor(progressMs: number, win: DrawWindow): number {
  if (progressMs <= win.start) return 0;
  if (progressMs >= win.end) return 1;
  const t = (progressMs - win.start) / (win.end - win.start);
  return t * t * (3 - 2 * t); // smoothstep
}

/** Left-to-right reveal mask for the wipe. Returns no mask once fully drawn so
 * the right edge isn't subtly clipped. */
export function wipeMask(reveal: number): CSSProperties {
  if (reveal >= 1) return {};
  const edge = reveal * 100;
  const mask = `linear-gradient(to right, #000 ${Math.max(0, edge - 7).toFixed(2)}%, transparent ${edge.toFixed(2)}%)`;
  return { WebkitMaskImage: mask, maskImage: mask };
}

// --- board ------------------------------------------------------------------

/** Soft drop-shadow for image cut-outs on the board (light theme: gentle). */
export const inkShadow: CSSProperties = {
  filter: 'drop-shadow(0 8px 16px rgba(0,0,0,0.12))',
};

/** The whiteboard surface: a clean near-white sheet with a soft inner vignette
 * and a hand-drawn marker border framing the board. No SVG filters/textures —
 * cheap to paint and identical in browser + Remotion. The border draws itself in
 * over the scene's first stretch so the board feels set up by hand. */
export function WhiteboardSheet({ theme, reveal = 1 }: { theme: SceneTheme; reveal?: number }) {
  const { palette, texture } = resolveTokens(theme);
  return (
    <div style={{ position: 'absolute', inset: 0, background: palette.bg, overflow: 'hidden' }}>
      <div style={{ position: 'absolute', inset: 0, ...textureStyle(texture, palette) }} />
      <div
        style={{
          position: 'absolute',
          inset: 0,
          background: `radial-gradient(120% 90% at 50% -20%, ${withAlpha(palette.accent, 0.05)} 0%, transparent 55%)`,
        }}
      />
      <div style={{ position: 'absolute', inset: 0, boxShadow: 'inset 0 0 200px rgba(0,0,0,0.05)' }} />
      {/* hand-drawn frame just inside the edges */}
      <div style={{ position: 'absolute', inset: '2.4cqw' }}>
        <Sketch d={wobblyRect(seedFrom('board-frame'), 1.1)} reveal={reveal} color={withAlpha(palette.ink, 0.33)} width={1.6} />
      </div>
    </div>
  );
}
