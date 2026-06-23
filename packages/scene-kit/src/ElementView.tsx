import katex from 'katex';
import 'katex/dist/katex.min.css';
import type { ComponentType, CSSProperties, ReactNode } from 'react';
import { canvasMeasure, fitFontCqw, STAGE_H, STAGE_W, type FitOpts, type Measure } from './fit';
import { seedFromId, sketchLine, sketchRect } from './sketch';
import { StickFigure } from './StickFigure';
import type { Element, Frame, SceneTheme, WordTiming } from './types';

// Headings & card titles render in a hand-drawn display face; body text uses the
// theme's modern sans (theme.font). Loaded by this real family name in both the
// web player and the Remotion render, so measurement and output match.
const HEADING_FAMILY = 'Caveat, cursive';

// Memoize one measurer per (family, weight) so we don't recreate the canvas ctx.
const measurers = new Map<string, Measure>();
function measureFor(fontFamily: string, weight: number): Measure {
  const key = `${weight} ${fontFamily}`;
  let m = measurers.get(key);
  if (!m) {
    m = canvasMeasure(fontFamily, weight);
    measurers.set(key, m);
  }
  return m;
}

/** Font size (cqw) that makes `text` fit `frame` — text never overflows its box. */
function fitted(text: string, frame: Frame, fontFamily: string, weight: number, opts: FitOpts): string {
  return `${fitFontCqw(text, frame, opts, measureFor(fontFamily, weight))}cqw`;
}

function escapeRegExp(s: string): string {
  return s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

/** Clamp text to `lines` lines so long content never overflows its frame. */
function clampLines(lines: number): CSSProperties {
  return {
    display: '-webkit-box',
    WebkitLineClamp: lines,
    WebkitBoxOrient: 'vertical',
    overflow: 'hidden',
  };
}

/** Wrap any emphasised terms found in `text` in a highlighted span. */
function withEmphasis(
  text: string,
  terms: string[] | null | undefined,
  color: string,
): ReactNode {
  const list = (terms ?? []).map((t) => t.trim()).filter(Boolean);
  if (list.length === 0) return text;
  const re = new RegExp(`(${list.map(escapeRegExp).join('|')})`, 'gi');
  const lower = new Set(list.map((t) => t.toLowerCase()));
  return text.split(re).map((part, i) =>
    lower.has(part.toLowerCase()) ? (
      <span key={i} style={{ color, fontWeight: 700 }}>
        {part}
      </span>
    ) : (
      part
    ),
  );
}

// Font sizes use container query units (cqw) so the stage scales at any size —
// identical math in the live player and the Remotion frame (whose root sets a
// container, see SceneStage).
/** Host-injectable image component. The web player uses a plain `<img>`; the
 * Remotion exporter passes its `<Img>`, which blocks the render until the image
 * loads (a plain `<img>` is NOT awaited, so it renders blank in the MP4). */
export type ImgComponent = ComponentType<{ src: string; style?: CSSProperties; alt?: string }>;

export function ElementView({
  element,
  theme,
  progress = 1,
  progressMs = 0,
  words,
  Img,
  imageObjectFit = 'contain',
}: {
  element: Element;
  theme: SceneTheme;
  progress?: number;
  progressMs?: number;
  words?: WordTiming[];
  Img?: ImgComponent;
  imageObjectFit?: 'cover' | 'contain';
}) {
  switch (element.type) {
    case 'heading': {
      const size = fitted(element.text ?? '', element.frame, HEADING_FAMILY, 700, { minPx: 18, maxPx: 96, lineHeight: 1.1 });
      return (
        <div style={{ fontFamily: HEADING_FAMILY, fontSize: size, fontWeight: 700, lineHeight: 1.1, ...clampLines(3) }}>
          {withEmphasis(element.text ?? '', element.emphasis, theme.primary)}
        </div>
      );
    }
    case 'text': {
      const size = fitted(element.text ?? '', element.frame, theme.font, 400, { minPx: 14, maxPx: 48, lineHeight: 1.4 });
      return (
        <div style={{ fontSize: size, lineHeight: 1.4, ...clampLines(4) }}>
          {withEmphasis(element.text ?? '', element.emphasis, theme.primary)}
        </div>
      );
    }
    case 'bullets': {
      const joined = (element.items ?? []).join(' ');
      const size = fitted(joined, element.frame, theme.font, 400, { minPx: 14, maxPx: 44, lineHeight: 1.35 });
      return (
        <ul style={{ margin: 0, paddingLeft: '1.1em', fontSize: size, lineHeight: 1.4 }}>
          {(element.items ?? []).map((item, i) => (
            <li key={i} style={{ marginBottom: '0.35em', ...clampLines(2) }}>
              {withEmphasis(item, element.emphasis, theme.primary)}
            </li>
          ))}
        </ul>
      );
    }
    case 'latex':
      return <Latex expression={element.latex ?? ''} color={theme.primary} />;
    case 'code':
      return (
        <pre
          style={{
            margin: 0,
            fontFamily: 'var(--font-mono), monospace',
            fontSize: '2.1cqw',
            background: 'rgba(0,0,0,0.35)',
            padding: '0.8em 1em',
            whiteSpace: 'pre-wrap',
          }}
        >
          {element.text}
        </pre>
      );
    case 'image': {
      if (!element.src) return null;
      const ImgTag = Img ?? 'img';
      return <ImgTag src={element.src} alt="" style={{ width: '100%', height: '100%', objectFit: imageObjectFit }} />;
    }
    case 'card': {
      if (theme.sketch) return <SketchCard element={element} theme={theme} />;
      const size = fitted(element.text ?? '', element.frame, HEADING_FAMILY, 600, { minPx: 12, maxPx: 38, lineHeight: 1.2 });
      return (
        <div
          style={{
            width: '100%',
            height: '100%',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            textAlign: 'center',
            padding: '0.6em',
            border: `0.35cqw solid ${theme.primary}`,
            borderRadius: '0.6cqw',
            background: 'rgba(255,255,255,0.05)',
            color: theme.foreground,
            fontFamily: HEADING_FAMILY,
            fontSize: size,
            fontWeight: 600,
            lineHeight: 1.2,
            boxSizing: 'border-box',
            overflow: 'hidden',
          }}
        >
          <span style={{ ...clampLines(4) }}>{element.text}</span>
        </div>
      );
    }
    case 'character':
      return (
        <StickFigure
          progressMs={progressMs}
          words={words}
          emotion={(element.style?.emotion as string) ?? 'neutral'}
          theme={theme}
        />
      );
    case 'shape':
      if (element.shape === 'arrow') {
        return (
          <Arrow
            dir={dirOf(element)}
            label={element.text ?? null}
            color={theme.primary}
            progress={progress}
            sketch={theme.sketch ?? false}
            seed={seedFromId(element.id)}
          />
        );
      }
      return <div style={shapeStyle(element, theme)} />;
    default:
      return null;
  }
}

function Latex({ expression, color }: { expression: string; color: string }) {
  const html = katex.renderToString(expression, { throwOnError: false, displayMode: true });
  return (
    <div style={{ fontSize: '3.4cqw', color }} dangerouslySetInnerHTML={{ __html: html }} />
  );
}

function shapeStyle(element: Element, theme: SceneTheme): CSSProperties {
  const base: CSSProperties = { width: '100%', height: '100%', background: theme.primary };
  if (element.shape === 'ellipse') return { ...base, borderRadius: '50%' };
  if (element.shape === 'line') return { height: 4, background: theme.primary };
  return base;
}

function dirOf(element: Element): 'right' | 'down' {
  return (element.style?.dir as 'right' | 'down') === 'down' ? 'down' : 'right';
}

/** A diagram card with a hand-drawn (Rough.js) border — the whiteboard look.
 * The border is seeded from the element id so it's identical every render. */
function SketchCard({ element, theme }: { element: Element; theme: SceneTheme }) {
  const fw = element.frame.w * STAGE_W;
  const fh = element.frame.h * STAGE_H;
  const paths = sketchRect(fw, fh, { seed: seedFromId(element.id), stroke: theme.primary, strokeWidth: 2.6 });
  return (
    <div
      style={{
        position: 'relative',
        width: '100%',
        height: '100%',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        textAlign: 'center',
        padding: '0.7em',
        boxSizing: 'border-box',
      }}
    >
      <svg
        viewBox={`0 0 ${fw} ${fh}`}
        preserveAspectRatio="none"
        style={{ position: 'absolute', inset: 0, width: '100%', height: '100%' }}
      >
        {paths.map((p, i) => (
          <path key={i} d={p.d} stroke={p.stroke} strokeWidth={p.strokeWidth} fill="none" strokeLinecap="round" />
        ))}
      </svg>
      <span
        style={{
          position: 'relative',
          color: theme.foreground,
          fontFamily: HEADING_FAMILY,
          fontSize: fitted(element.text ?? '', element.frame, HEADING_FAMILY, 600, { minPx: 12, maxPx: 38, lineHeight: 1.2 }),
          fontWeight: 600,
          lineHeight: 1.2,
          ...clampLines(4),
        }}
      >
        {element.text}
      </span>
    </div>
  );
}

/** A connector arrow that *draws itself in*: the line grows from 0→full with
 * `progress`, then the head and label appear. In `sketch` mode the line is a
 * hand-drawn Rough.js stroke (whiteboard look). Pure function of `progress` +
 * `seed`, so it animates identically in the player and the MP4. */
function Arrow({
  dir,
  label,
  color,
  progress = 1,
  sketch = false,
  seed = 1,
}: {
  dir: 'right' | 'down';
  label: string | null;
  color: string;
  progress?: number;
  sketch?: boolean;
  seed?: number;
}) {
  const right = dir === 'right';
  const p = Math.max(0, Math.min(1, progress));
  // Head/label reveal only once the line has essentially finished drawing.
  const headOpacity = p > 0.85 ? 1 : 0;
  const labelOpacity = Math.max(0, Math.min(1, (p - 0.6) / 0.4));
  const head: CSSProperties = right
    ? {
        right: '-1px',
        top: '50%',
        transform: 'translateY(-50%)',
        borderTop: '0.7cqw solid transparent',
        borderBottom: '0.7cqw solid transparent',
        borderLeft: `1cqw solid ${color}`,
      }
    : {
        bottom: '-1px',
        left: '50%',
        transform: 'translateX(-50%)',
        borderLeft: '0.7cqw solid transparent',
        borderRight: '0.7cqw solid transparent',
        borderTop: `1cqw solid ${color}`,
      };

  let lineEl: ReactNode;
  if (sketch) {
    // Rough stroke in a 0..100 box; `pathLength=1` lets us draw it in via
    // dashoffset regardless of the (wobbly) path's true length.
    const paths = right
      ? sketchLine(4, 50, 92, 50, { seed, stroke: color, strokeWidth: 2.6 })
      : sketchLine(50, 4, 50, 92, { seed, stroke: color, strokeWidth: 2.6 });
    lineEl = (
      <svg
        viewBox="0 0 100 100"
        preserveAspectRatio="none"
        style={{ position: 'absolute', inset: 0, width: '100%', height: '100%', overflow: 'visible' }}
      >
        {paths.map((pth, i) => (
          <path
            key={i}
            d={pth.d}
            stroke={pth.stroke}
            strokeWidth={pth.strokeWidth}
            fill="none"
            strokeLinecap="round"
            pathLength={1}
            strokeDasharray={1}
            strokeDashoffset={1 - p}
          />
        ))}
      </svg>
    );
  } else {
    // Clean line grows along its axis; the cross-axis stays centered.
    const grown = `${(p * 100).toFixed(2)}%`;
    const line: CSSProperties = right
      ? { top: '50%', left: 0, width: grown, height: '0.4cqw', transform: 'translateY(-50%)', borderRadius: '0.2cqw' }
      : { left: '50%', top: 0, height: grown, width: '0.4cqw', transform: 'translateX(-50%)', borderRadius: '0.2cqw' };
    lineEl = <div style={{ position: 'absolute', background: color, ...line }} />;
  }

  return (
    <div style={{ position: 'relative', width: '100%', height: '100%' }}>
      {lineEl}
      <div style={{ position: 'absolute', width: 0, height: 0, opacity: headOpacity, ...head }} />
      {label ? (
        <div
          style={{
            position: 'absolute',
            top: '50%',
            left: '50%',
            transform: 'translate(-50%, -50%)',
            fontSize: '1.7cqw',
            color: 'rgba(255,255,255,0.95)', // light text on the dark pill, readable on any theme
            background: 'rgba(0,0,0,0.62)',
            padding: '0.1em 0.4em',
            borderRadius: '0.3cqw',
            whiteSpace: 'nowrap',
            maxWidth: '100%',
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            boxSizing: 'border-box',
            opacity: labelOpacity,
          }}
        >
          {label}
        </div>
      ) : null}
    </div>
  );
}
