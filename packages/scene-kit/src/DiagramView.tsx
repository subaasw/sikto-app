import type { CSSProperties } from 'react';
import { Hand } from './Hand';
import { DEFAULT_SCENE_MS, type Element, type Frame, type SceneTheme } from './types';
import { drawWindows, revealFor, WhiteboardSheet, wipeMask } from './whiteboard';
import { TYPE_SCALE, resolveTokens } from './tokens';

/**
 * A drawn-diagram scene: the Python builder lays out `elements` (heading + cards
 * + arrows, frames in 0..1) and we *draw* them one at a time in document order —
 * rounded-rect cards self-draw via stroke-dashoffset, arrows draw between the
 * cards they connect, the hand rides whichever element is currently drawing.
 * No per-frame randomness → nothing shakes, identical in browser + Remotion.
 */
export function DiagramView({
  elements,
  theme,
  progressMs,
  sceneDurationMs,
}: {
  elements: Element[];
  theme: SceneTheme;
  progressMs: number;
  sceneDurationMs?: number;
}) {
  const { palette } = resolveTokens(theme);
  const items = elements.filter((e) => e.frame);
  const windows = drawWindows(items.length, sceneDurationMs ?? DEFAULT_SCENE_MS);
  const reveals = items.map((_, i) => revealFor(progressMs, windows[i]));

  // The hand rides the wipe edge of whichever element is currently drawing.
  const active = windows.findIndex((w) => progressMs > w.start && progressMs < w.end);
  let hand: { x: number; y: number } | null = null;
  if (active >= 0) {
    const f = items[active].frame;
    hand = { x: (f.x + reveals[active] * f.w) * 100, y: (f.y + f.h * 0.5) * 100 };
  }

  return (
    <div style={{ position: 'absolute', inset: 0 }}>
      <WhiteboardSheet theme={theme} />
      {/* Arrows live in one stage-spanning SVG so they can span between cards. */}
      <svg
        viewBox="0 0 100 100"
        preserveAspectRatio="none"
        style={{ position: 'absolute', inset: 0, width: '100%', height: '100%', overflow: 'visible' }}
      >
        {items.map((e, i) =>
          e.shape === 'arrow' ? (
            <Arrow key={i} element={e} cards={items} ink={palette.ink} reveal={reveals[i]} />
          ) : null,
        )}
      </svg>
      {items.map((e, i) =>
        e.type === 'card' ? (
          <Card key={i} element={e} theme={theme} reveal={reveals[i]} />
        ) : e.shape === 'arrow' ? null : (
          <Text key={i} element={e} theme={theme} reveal={reveals[i]} />
        ),
      )}
      {hand && <Hand x={hand.x} y={hand.y} color={palette.accent} />}
    </div>
  );
}

const center = (f: Frame) => ({ x: f.x + f.w / 2, y: f.y + f.h / 2 });

function boxOf(f: Frame): CSSProperties {
  return {
    position: 'absolute',
    left: `${f.x * 100}%`,
    top: `${f.y * 100}%`,
    width: `${f.w * 100}%`,
    height: `${f.h * 100}%`,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
  };
}

/** A card: a self-drawing rounded rect, its label fading in as the box completes. */
function Card({ element, theme, reveal }: { element: Element; theme: SceneTheme; reveal: number }) {
  const { palette, fonts } = resolveTokens(theme);
  const textReveal = Math.max(0, Math.min(1, (reveal - 0.5) / 0.5));
  return (
    <div style={boxOf(element.frame)}>
      <svg
        viewBox="0 0 100 60"
        preserveAspectRatio="none"
        style={{ position: 'absolute', inset: 0, width: '100%', height: '100%' }}
      >
        <rect
          x={3}
          y={3}
          width={94}
          height={54}
          rx={7}
          fill="none"
          stroke={palette.ink}
          strokeWidth={2}
          vectorEffect="non-scaling-stroke"
          pathLength={1}
          strokeDasharray={1}
          strokeDashoffset={1 - reveal}
        />
      </svg>
      <span
        style={{
          fontFamily: fonts.body,
          fontWeight: 700,
          fontSize: `${TYPE_SCALE.body.size}cqw`,
          color: palette.ink,
          lineHeight: 1.18,
          textAlign: 'center',
          padding: '0 1cqw',
          opacity: textReveal,
        }}
      >
        {element.text}
      </span>
    </div>
  );
}

/** Heading / free label: marker text wiped on left-to-right. */
function Text({ element, theme, reveal }: { element: Element; theme: SceneTheme; reveal: number }) {
  const { palette, fonts } = resolveTokens(theme);
  if (!element.text) return null;
  const isHead = element.type === 'heading';
  return (
    <div style={{ ...boxOf(element.frame), ...wipeMask(reveal) }}>
      <span
        style={{
          fontFamily: isHead ? fonts.display : fonts.body,
          fontWeight: isHead ? 800 : 600,
          fontSize: isHead ? `${TYPE_SCALE.h1.size}cqw` : `${TYPE_SCALE.body.size}cqw`,
          color: palette.ink,
          lineHeight: 1.18,
          textAlign: 'center',
          padding: '0 1cqw',
          letterSpacing: isHead ? '-0.01em' : undefined,
        }}
      >
        {element.text}
      </span>
    </div>
  );
}

/** An arrow from the card before this element to the card after it (document
 * order), drawn edge-to-edge. ponytail: arrowheads skew slightly on non-1:1
 * aspect (stretched viewBox); fine at this size. */
function Arrow({
  element,
  cards,
  ink,
  reveal,
}: {
  element: Element;
  cards: Element[];
  ink: string;
  reveal: number;
}) {
  const i = cards.indexOf(element);
  const prev = [...cards.slice(0, i)].reverse().find((e) => e.type === 'card');
  const next = cards.slice(i + 1).find((e) => e.type === 'card');
  if (!prev || !next) return null;

  const pc = center(prev.frame);
  const nc = center(next.frame);
  const dx = nc.x - pc.x;
  const dy = nc.y - pc.y;
  const horizontal = Math.abs(dx) >= Math.abs(dy);

  let sx: number, sy: number, ex: number, ey: number;
  if (horizontal) {
    sy = pc.y * 100;
    ey = nc.y * 100;
    sx = (dx > 0 ? prev.frame.x + prev.frame.w : prev.frame.x) * 100;
    ex = (dx > 0 ? next.frame.x : next.frame.x + next.frame.w) * 100;
  } else {
    sx = pc.x * 100;
    ex = nc.x * 100;
    sy = (dy > 0 ? prev.frame.y + prev.frame.h : prev.frame.y) * 100;
    ey = (dy > 0 ? next.frame.y : next.frame.y + next.frame.h) * 100;
  }

  // Shorten the line so the arrowhead sits at the card edge.
  const len = Math.hypot(ex - sx, ey - sy) || 1;
  const ux = (ex - sx) / len;
  const uy = (ey - sy) / len;
  const tipX = ex - ux * 1.5;
  const tipY = ey - uy * 1.5;
  const HEAD = 3.2;
  const head = (ang: number) => {
    const a = Math.atan2(uy, ux) + ang;
    return `${tipX - Math.cos(a) * HEAD},${tipY - Math.sin(a) * HEAD}`;
  };

  return (
    <g stroke={ink} strokeWidth={2} fill="none" vectorEffect="non-scaling-stroke" strokeLinecap="round">
      <line
        x1={sx}
        y1={sy}
        x2={tipX}
        y2={tipY}
        pathLength={1}
        strokeDasharray={1}
        strokeDashoffset={1 - reveal}
      />
      <polyline
        points={`${head(0.45)} ${tipX},${tipY} ${head(-0.45)}`}
        opacity={reveal > 0.7 ? 1 : 0}
        strokeLinejoin="round"
      />
    </g>
  );
}
