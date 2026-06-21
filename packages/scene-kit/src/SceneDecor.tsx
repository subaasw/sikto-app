import type { SceneTheme } from './types';

/**
 * Subtle "designed template" framing: a per-scene progress line along the top
 * and a small brand accent in the corner. Theme-driven, so a template's palette
 * recolours it automatically. Driven by `progressMs` for the progress motion.
 */
export function SceneDecor({
  theme,
  progressMs,
  sceneDurationMs,
}: {
  theme: SceneTheme;
  progressMs: number;
  sceneDurationMs?: number;
}) {
  const pct =
    sceneDurationMs && sceneDurationMs > 0
      ? Math.max(0, Math.min(1, progressMs / sceneDurationMs))
      : 0;

  return (
    <div style={{ position: 'absolute', inset: 0, pointerEvents: 'none' }}>
      {/* per-scene progress line */}
      <div
        style={{
          position: 'absolute',
          top: 0,
          left: 0,
          height: '0.4cqw',
          width: `${pct * 100}%`,
          background: theme.primary,
          opacity: 0.85,
        }}
      />
      {/* corner brand accent */}
      <div style={{ position: 'absolute', top: '3.5%', left: '4%', display: 'flex', gap: '0.6cqw' }}>
        <div style={{ width: '2.6cqw', height: '0.7cqw', background: theme.primary }} />
        <div style={{ width: '0.7cqw', height: '0.7cqw', background: theme.primary, opacity: 0.5 }} />
      </div>
    </div>
  );
}
