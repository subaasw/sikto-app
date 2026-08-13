// The design system's single source of visual truth. Every color, size, and
// texture the engine paints comes from here (Hand.tsx's illustration and the
// #000 of reveal masks are the only exemptions). Mirrored by the API in
// api/scenes/schema.py (Palette) — keep the two in sync.
//
// Sizes are cqw (container width %): 1 cqw = 19.2 px on the 1920-wide canvas.
// Legibility floors from https://legibility.info/rules-for-text-in-videos:
// body ≥ 40 px @1080p → ≥ 2.08 cqw. Enforced in test/tokens.test.ts.

import type { SceneTheme } from './types';

// --- color roles -------------------------------------------------------------

/** Role-based palette; generalizes motion-kit's MotionPalette engine-wide. */
export interface Palette {
  bg: string; // canvas
  surface: string; // cards / panels
  ink: string; // primary text + strokes that read as writing
  soft: string; // supporting text
  accent: string; // marker #1: underlines, arrows, emphasis
  accent2: string; // marker #2: circles, callouts (two-marker board language)
  accent_ink: string; // text set ON the accent (chips, CTAs)
  stroke: string; // frames, hairlines, connectors
  wash: string; // large tinted fields (card fills, highlight blocks)
}

export type Texture = 'graph' | 'grain' | 'none';

export interface FontSet {
  display: string; // headings — the template's characterful face
  body: string; // bullets, labels, captions
  script: string; // the board handwriting (reads as WRITING when wiped on)
}

export interface Tokens {
  palette: Palette;
  fonts: FontSet;
  texture: Texture;
}

// --- type scale ----------------------------------------------------------------

export type TypeRole = 'display' | 'h1' | 'h2' | 'body' | 'caption' | 'scriptHead' | 'scriptBody';

export interface TypeSpec {
  size: number; // cqw
  weight: number;
  lineHeight: number;
  letterSpacing: string;
}

/** Minimum body/caption size (cqw) — 40 px at 1080p per legibility.info. */
export const MIN_TEXT_CQW = 2.08;

export const TYPE_SCALE: Record<TypeRole, TypeSpec> = {
  display: { size: 7.0, weight: 800, lineHeight: 1.04, letterSpacing: '-0.02em' },
  h1: { size: 5.2, weight: 700, lineHeight: 1.1, letterSpacing: '-0.015em' },
  h2: { size: 3.6, weight: 700, lineHeight: 1.15, letterSpacing: '-0.01em' },
  body: { size: 2.6, weight: 500, lineHeight: 1.35, letterSpacing: '0' },
  caption: { size: 2.1, weight: 600, lineHeight: 1.3, letterSpacing: '0.01em' },
  // Caveat has a small x-height; script sizes run larger to hit the same
  // optical size as body/display (values preserved from the proven board look).
  scriptHead: { size: 6.8, weight: 700, lineHeight: 1.12, letterSpacing: '0' },
  scriptBody: { size: 4.1, weight: 600, lineHeight: 1.12, letterSpacing: '0' },
};

/** CSS for a type role (font family comes from the token set). */
export function typeStyle(role: TypeRole, family: string): {
  fontFamily: string;
  fontWeight: number;
  fontSize: string;
  lineHeight: number;
  letterSpacing: string;
} {
  const t = TYPE_SCALE[role];
  return {
    fontFamily: family,
    fontWeight: t.weight,
    fontSize: `${t.size}cqw`,
    lineHeight: t.lineHeight,
    letterSpacing: t.letterSpacing,
  };
}

// --- space / stroke / radius ---------------------------------------------------

export const SPACE = { xs: 0.6, sm: 1.2, md: 2.4, lg: 3.6, xl: 4.8 } as const; // cqw
export const RADIUS = { card: 0.8, chip: 3 } as const; // cqw
export const STROKE = { hairline: 1.2, line: 1.8, marker: 3, bold: 4.5 } as const; // Sketch/SVG units
/** Keep meaningful content inside this margin (action-safe ≈ 5%). */
export const SAFE_MARGIN_CQW = 5;

// --- template token sets ---------------------------------------------------------

const GEIST = 'Geist, "Inter", system-ui, sans-serif';
const CAVEAT = '"Caveat", "Comic Sans MS", cursive';

export const TEMPLATE_TOKENS: Record<string, Tokens> = {
  // Cool graph-paper field notes: spruce ink, emerald + sienna markers.
  explainer: {
    palette: {
      bg: '#f4f6f2',
      surface: '#ffffff',
      ink: '#1b2a24',
      soft: '#51645b',
      accent: '#0c7a58',
      accent2: '#c2542e',
      accent_ink: '#ffffff',
      stroke: '#9db0a6',
      wash: '#e3ede6',
    },
    fonts: { display: '"Bricolage Grotesque", ' + GEIST, body: GEIST, script: CAVEAT },
    texture: 'graph',
  },
  // A true board: slate ink, blue + red markers.
  whiteboard: {
    palette: {
      bg: '#f8fafc',
      surface: '#ffffff',
      ink: '#1e2937',
      soft: '#5a6b7d',
      accent: '#2456c9',
      accent2: '#cc4444',
      accent_ink: '#ffffff',
      stroke: '#93a3b3',
      wash: '#e7eef7',
    },
    fonts: { display: CAVEAT, body: GEIST, script: CAVEAT },
    texture: 'grain',
  },
  // Ember dark — matches motion-kit's `ember` so slide + motion scenes cohere.
  marketing: {
    palette: {
      bg: '#171112',
      surface: '#26191b',
      ink: '#faeeea',
      soft: '#c9a29b',
      accent: '#f4b642',
      accent2: '#ff8a5c',
      accent_ink: '#231505',
      stroke: '#4a3a35',
      wash: '#26191b',
    },
    fonts: { display: '"Archivo Black", ' + GEIST, body: GEIST, script: CAVEAT },
    texture: 'grain',
  },
};

export const DEFAULT_TEMPLATE_TOKENS = TEMPLATE_TOKENS.explainer;

// --- resolution -------------------------------------------------------------------

/** Tokens for a theme. Prefers the theme's own palette/fonts/texture (API-built
 * lessons), falls back to its template's token set, and folds in a legacy
 * primary/background/foreground trio if the LLM director repainted those. */
export function resolveTokens(theme: SceneTheme): Tokens {
  const base = TEMPLATE_TOKENS[theme.template ?? ''] ?? DEFAULT_TEMPLATE_TOKENS;
  const palette: Palette = { ...base.palette, ...(theme.palette ?? {}) };
  if (!theme.palette) {
    // Legacy trio only: honour a director repaint without losing the roles.
    if (theme.background && theme.background !== base.palette.bg) {
      palette.bg = theme.background;
      palette.surface = theme.background;
      palette.wash = withAlpha(theme.primary ?? palette.accent, 0.12);
    }
    if (theme.foreground && theme.foreground !== base.palette.ink) {
      palette.ink = theme.foreground;
      palette.soft = withAlpha(theme.foreground, 0.72);
      palette.stroke = withAlpha(theme.foreground, 0.45);
    }
    if (theme.primary && theme.primary !== base.palette.accent) palette.accent = theme.primary;
  }
  return {
    palette,
    fonts: theme.fonts ?? base.fonts,
    texture: theme.texture ?? base.texture,
  };
}

// --- texture -----------------------------------------------------------------------

/** Background-image CSS for a template texture. Static tiles (no live SVG
 * filters) so it paints cheap and identical in browser + Remotion. */
export function textureStyle(texture: Texture, palette: Palette): {
  backgroundImage?: string;
  backgroundSize?: string;
} {
  if (texture === 'graph') {
    const line = withAlpha(palette.stroke, 0.28);
    return {
      backgroundImage: `linear-gradient(${line} 1px, transparent 1px), linear-gradient(90deg, ${line} 1px, transparent 1px)`,
      backgroundSize: '3cqw 3cqw',
    };
  }
  if (texture === 'grain') {
    const [r, g, b] = [channel(palette.ink, 0) / 255, channel(palette.ink, 1) / 255, channel(palette.ink, 2) / 255];
    const svg =
      `<svg xmlns='http://www.w3.org/2000/svg' width='240' height='240'>` +
      `<filter id='n'><feTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='2' stitchTiles='stitch'/>` +
      `<feColorMatrix values='0 0 0 0 ${r.toFixed(3)} 0 0 0 0 ${g.toFixed(3)} 0 0 0 0 ${b.toFixed(3)} 0 0 0 0.055 0'/></filter>` +
      `<rect width='100%' height='100%' filter='url(%23n)'/></svg>`;
    return { backgroundImage: `url("data:image/svg+xml,${svg.replace(/</g, '%3C').replace(/>/g, '%3E').replace(/#/g, '%23')}")` };
  }
  return {};
}

// --- color math ----------------------------------------------------------------------

function channel(hex: string, i: number): number {
  const h = hex.replace('#', '');
  const full = h.length === 3 ? h.split('').map((c) => c + c).join('') : h;
  return parseInt(full.slice(i * 2, i * 2 + 2), 16);
}

/** `rgba()` string from a hex color. */
export function withAlpha(hex: string, alpha: number): string {
  return `rgba(${channel(hex, 0)},${channel(hex, 1)},${channel(hex, 2)},${alpha})`;
}

function luminance(hex: string): number {
  const lin = (c: number) => {
    const s = c / 255;
    return s <= 0.03928 ? s / 12.92 : Math.pow((s + 0.055) / 1.055, 2.4);
  };
  return 0.2126 * lin(channel(hex, 0)) + 0.7152 * lin(channel(hex, 1)) + 0.0722 * lin(channel(hex, 2));
}

/** WCAG contrast ratio between two hex colors (1..21). */
export function contrastRatio(a: string, b: string): number {
  const [hi, lo] = [luminance(a), luminance(b)].sort((x, y) => y - x);
  return (hi + 0.05) / (lo + 0.05);
}
