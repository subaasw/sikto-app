import type { CSSProperties, ReactElement } from 'react';
import type { SceneTheme } from '../types';

function hexToRgb(hex: string): [number, number, number] {
  const h = hex.replace('#', '');
  const full = h.length === 3 ? h.split('').map((c) => c + c).join('') : h;
  const int = parseInt(full || '000000', 16);
  return [(int >> 16) & 255, (int >> 8) & 255, int & 255];
}

export function rgba(hex: string, a: number): string {
  const [r, g, b] = hexToRgb(hex);
  return `rgba(${r},${g},${b},${a})`;
}

// Static film grain (fractal noise). Never keyed to time → no frame-to-frame
// shimmer in the MP4.
const GRAIN =
  "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='160' height='160'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='2' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E";

/**
 * The scene background — deliberately one **static** treatment for every theme:
 * a solid dark fill, a faint corner vignette for depth, and a barely-there grain.
 * Decorative animated backgrounds were removed (they couldn't be customised and
 * their drift read as motion). `progressMs` is accepted but ignored so the
 * signature stays drop-in; `background_style` on the theme is now vestigial.
 */
export function renderBackground(theme: SceneTheme, _progressMs?: number): ReactElement {
  const base: CSSProperties = { position: 'absolute', inset: 0, background: theme.background };
  return (
    <div style={base}>
      {/* faint vignette: a touch of the accent up top, darkened corners */}
      <div
        style={{
          position: 'absolute',
          inset: 0,
          backgroundImage:
            `radial-gradient(circle at 50% 0%, ${rgba(theme.primary, 0.06)}, transparent 60%),` +
            `radial-gradient(circle at 50% 120%, rgba(0,0,0,0.45), transparent 60%)`,
        }}
      />
      {/* static grain for depth */}
      <div
        style={{
          position: 'absolute',
          inset: 0,
          backgroundImage: `url("${GRAIN}")`,
          backgroundSize: '24cqw 24cqw',
          opacity: 0.025, // barely-there: enough for depth, not a grungy/rusty texture
          mixBlendMode: 'overlay',
        }}
      />
    </div>
  );
}
