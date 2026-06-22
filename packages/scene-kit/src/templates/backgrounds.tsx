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

/** Slow drift offsets shared by the animated backgrounds. */
function drift(progressMs: number, period = 7000): [number, number] {
  const t = (Number.isFinite(progressMs) ? progressMs : 0) / period;
  return [Math.sin(t) * 7, Math.cos(t * 0.8) * 5];
}

const base = (theme: SceneTheme): CSSProperties => ({
  position: 'absolute',
  inset: 0,
  background: theme.background,
});

export function solidBg(theme: SceneTheme): ReactElement {
  return <div style={base(theme)} />;
}

export function gradientBg(theme: SceneTheme, progressMs: number): ReactElement {
  const [dx, dy] = drift(progressMs);
  return (
    <div
      style={{
        ...base(theme),
        backgroundImage:
          `radial-gradient(circle at ${28 + dx}% ${22 + dy}%, ${rgba(theme.primary, 0.14)}, transparent 55%),` +
          `linear-gradient(165deg, ${rgba(theme.foreground, 0.05)}, transparent 70%)`,
      }}
    />
  );
}

export function meshBg(theme: SceneTheme, progressMs: number): ReactElement {
  const [dx, dy] = drift(progressMs);
  return (
    <div
      style={{
        ...base(theme),
        backgroundImage:
          `radial-gradient(circle at ${24 + dx}% ${20 + dy}%, ${rgba(theme.primary, 0.16)}, transparent 50%),` +
          `radial-gradient(circle at ${82 - dx}% ${78 - dy}%, ${rgba(theme.foreground, 0.08)}, transparent 55%),` +
          `linear-gradient(160deg, ${rgba(theme.foreground, 0.04)}, transparent 70%)`,
      }}
    />
  );
}

export function gridBg(theme: SceneTheme, progressMs: number): ReactElement {
  const [dx, dy] = drift(progressMs);
  return (
    <div
      style={{
        ...base(theme),
        backgroundImage:
          `radial-gradient(circle at ${30 + dx}% ${25 + dy}%, ${rgba(theme.primary, 0.1)}, transparent 55%),` +
          `linear-gradient(${rgba(theme.foreground, 0.05)} 1px, transparent 1px),` +
          `linear-gradient(90deg, ${rgba(theme.foreground, 0.05)} 1px, transparent 1px)`,
        backgroundSize: '100% 100%, 5cqw 5cqw, 5cqw 5cqw',
      }}
    />
  );
}

// Static film grain (fractal noise). Fixed — never keyed to progressMs — so it
// does not shimmer frame-to-frame in the MP4.
const GRAIN =
  "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='160' height='160'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='2' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E";

/** Marketing's rustic/grungy texture: moving accent blobs + halftone + grain. */
export function textureBg(theme: SceneTheme, progressMs: number): ReactElement {
  const t = (Number.isFinite(progressMs) ? progressMs : 0) / 1000;
  const b1x = 24 + Math.sin(t * 0.5) * 13;
  const b1y = 30 + Math.cos(t * 0.4) * 11;
  const b2x = 78 + Math.sin(t * 0.37 + 2) * 12;
  const b2y = 66 + Math.cos(t * 0.6 + 1) * 13;
  return (
    <div style={base(theme)}>
      {/* two drifting accent blobs — constant 2D motion */}
      <div
        style={{
          position: 'absolute',
          inset: 0,
          backgroundImage:
            `radial-gradient(circle at ${b1x}% ${b1y}%, ${rgba(theme.primary, 0.24)}, transparent 40%),` +
            `radial-gradient(circle at ${b2x}% ${b2y}%, ${rgba(theme.foreground, 0.09)}, transparent 44%)`,
        }}
      />
      {/* halftone dots */}
      <div
        style={{
          position: 'absolute',
          inset: 0,
          backgroundImage: `radial-gradient(${rgba(theme.foreground, 0.07)} 0.55px, transparent 0.7px)`,
          backgroundSize: '1.6cqw 1.6cqw',
        }}
      />
      {/* film grain */}
      <div
        style={{
          position: 'absolute',
          inset: 0,
          backgroundImage: `url("${GRAIN}")`,
          backgroundSize: '24cqw 24cqw',
          opacity: 0.1,
          mixBlendMode: 'overlay',
        }}
      />
    </div>
  );
}
