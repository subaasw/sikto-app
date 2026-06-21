import type { CSSProperties } from 'react';
import type { SceneTheme } from './types';

function hexToRgb(hex: string): [number, number, number] {
  const h = hex.replace('#', '');
  const full = h.length === 3 ? h.split('').map((c) => c + c).join('') : h;
  const int = parseInt(full || '000000', 16);
  return [(int >> 16) & 255, (int >> 8) & 255, int & 255];
}

function rgba(hex: string, a: number): string {
  const [r, g, b] = hexToRgb(hex);
  return `rgba(${r},${g},${b},${a})`;
}

/**
 * The scene's background layer: a tasteful, slowly-drifting gradient/mesh/grid
 * derived from the theme palette. Driven by `progressMs` so the motion is
 * identical in the live player and the Remotion render. Sits behind the content.
 */
export function SceneBackground({
  theme,
  progressMs,
}: {
  theme: SceneTheme;
  progressMs: number;
}) {
  const style = theme.background_style ?? 'gradient';
  const t = (Number.isFinite(progressMs) ? progressMs : 0) / 7000;
  const dx = Math.sin(t) * 7;
  const dy = Math.cos(t * 0.8) * 5;

  const base: CSSProperties = { position: 'absolute', inset: 0, background: theme.background };

  if (style === 'solid') return <div style={base} />;

  if (style === 'grid') {
    return (
      <div
        style={{
          ...base,
          backgroundImage:
            `radial-gradient(circle at ${30 + dx}% ${25 + dy}%, ${rgba(theme.primary, 0.1)}, transparent 55%),` +
            `linear-gradient(${rgba(theme.foreground, 0.05)} 1px, transparent 1px),` +
            `linear-gradient(90deg, ${rgba(theme.foreground, 0.05)} 1px, transparent 1px)`,
          backgroundSize: '100% 100%, 5cqw 5cqw, 5cqw 5cqw',
        }}
      />
    );
  }

  if (style === 'mesh') {
    return (
      <div
        style={{
          ...base,
          backgroundImage:
            `radial-gradient(circle at ${24 + dx}% ${20 + dy}%, ${rgba(theme.primary, 0.16)}, transparent 50%),` +
            `radial-gradient(circle at ${82 - dx}% ${78 - dy}%, ${rgba(theme.foreground, 0.08)}, transparent 55%),` +
            `linear-gradient(160deg, ${rgba(theme.foreground, 0.04)}, transparent 70%)`,
        }}
      />
    );
  }

  // gradient (default): a soft primary glow drifting over a subtle vertical wash.
  return (
    <div
      style={{
        ...base,
        backgroundImage:
          `radial-gradient(circle at ${28 + dx}% ${22 + dy}%, ${rgba(theme.primary, 0.14)}, transparent 55%),` +
          `linear-gradient(165deg, ${rgba(theme.foreground, 0.05)}, transparent 70%)`,
      }}
    />
  );
}
