import type { CSSProperties } from 'react';
import { RADIUS, SPACE, resolveTokens, typeStyle, withAlpha } from './tokens';
import type { ImgComponent, Layer, SceneTheme } from './types';

/**
 * The clean (non-sketch) slide renderer — a professional, editorial look for the
 * `explainer` family: display-face headlines, icons/visuals in surface tiles, and
 * one accent-keyline device (a growing underline, a left rule, a corner tab) that
 * ties every scene together. The whiteboard renderer (LayerView) is the sketch
 * counterpart; SceneStage picks between them on `theme.sketch`.
 *
 * `reveal` (0..1 across the layer's draw window) drives a snappy fade that settles
 * in the first half and holds — content arrives and stays, it never crawls in.
 */
function frameBox(layer: Layer): CSSProperties {
  const f = layer.frame ?? { x: 0.08, y: 0.12, w: 0.84, h: 0.2 };
  return {
    position: 'absolute',
    left: `${(f.x * 100).toFixed(2)}%`,
    top: `${(f.y * 100).toFixed(2)}%`,
    width: `${(f.w * 100).toFixed(2)}%`,
    height: `${(f.h * 100).toFixed(2)}%`,
  };
}

/** Ease-out that reaches 1 by the first half of the window, then holds. */
function ease(reveal: number): number {
  const t = Math.max(0, Math.min(1, reveal * 2));
  return 1 - (1 - t) ** 3;
}

function rise(reveal: number, cqw = 1.8): CSSProperties {
  const e = ease(reveal);
  return { opacity: e, transform: `translateY(${((1 - e) * cqw).toFixed(2)}cqw)` };
}

function pop(reveal: number): CSSProperties {
  const e = ease(reveal);
  return { opacity: e, transform: `scale(${(0.92 + 0.08 * e).toFixed(3)})` };
}

export function CleanLayerView({
  layer,
  theme,
  reveal,
  Img,
}: {
  layer: Layer;
  theme: SceneTheme;
  reveal: number;
  Img?: ImgComponent;
}) {
  const box = frameBox(layer);
  const { palette, fonts } = resolveTokens(theme);
  const e = ease(reveal);

  // Icon / illustration. Small layers read as an icon in a tinted chip; larger
  // ones as a clean surface card with a soft shadow and an accent corner tab.
  if (layer.kind === 'image') {
    if (!layer.content || !Img) return null;
    const isIcon = layer.size === 'sm';
    return (
      <div style={{ ...box, ...pop(reveal) }}>
        <div
          style={{
            position: 'relative',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            width: '100%',
            height: '100%',
            padding: `${isIcon ? SPACE.lg : SPACE.md}cqw`,
            background: isIcon ? withAlpha(palette.accent, 0.12) : palette.surface,
            borderRadius: `${isIcon ? RADIUS.chip : RADIUS.card}cqw`,
            border: `0.14cqw solid ${withAlpha(palette.stroke, 0.7)}`,
            boxShadow: `0 1.4cqw 3cqw ${withAlpha('#000000', 0.16)}`,
          }}
        >
          <Img
            src={layer.content}
            style={{ width: '100%', height: '100%', objectFit: 'contain' }}
          />
          {!isIcon && (
            <div
              style={{
                position: 'absolute',
                top: 0,
                left: `${SPACE.md}cqw`,
                width: `${SPACE.lg}cqw`,
                height: '0.5cqw',
                background: palette.accent,
                borderRadius: '0 0 0.3cqw 0.3cqw',
              }}
            />
          )}
        </div>
      </div>
    );
  }

  // Emphasised keyword → a solid accent chip.
  if (layer.kind === 'sticker') {
    if (!layer.content) return null;
    return (
      <div style={{ ...box, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <span
          style={{
            ...pop(reveal),
            display: 'inline-flex',
            alignItems: 'center',
            padding: `${SPACE.xs}cqw ${SPACE.md}cqw`,
            background: palette.accent,
            color: palette.accent_ink,
            borderRadius: `${RADIUS.chip}cqw`,
            ...typeStyle('caption', fonts.body),
            fontWeight: 700,
          }}
        >
          {layer.content}
        </span>
      </div>
    );
  }

  // A clean accent rule (grows in from the left).
  if (layer.kind === 'shape') {
    return (
      <div style={box}>
        <div
          style={{
            position: 'absolute',
            left: 0,
            top: '45%',
            width: '100%',
            height: '0.9cqw',
            background: palette.accent,
            borderRadius: '0.5cqw',
            opacity: e,
            transformOrigin: 'left center',
            transform: `scaleX(${e.toFixed(3)})`,
          }}
        />
      </div>
    );
  }

  if (!layer.content) return null;

  // Headline: display face on ink, with a short accent underline growing beneath.
  if (layer.kind === 'headline') {
    return (
      <div
        style={{
          ...box,
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'flex-end',
          gap: `${SPACE.sm}cqw`,
        }}
      >
        <span style={{ ...rise(reveal, 2.2), ...typeStyle('h1', fonts.display), color: palette.ink }}>
          {layer.content}
        </span>
        <div
          style={{
            width: '20%',
            minWidth: '8cqw',
            height: '0.7cqw',
            background: palette.accent,
            borderRadius: '0.5cqw',
            transformOrigin: 'left center',
            transform: `scaleX(${e.toFixed(3)})`,
          }}
        />
      </div>
    );
  }

  // Caption / supporting text: body face on soft ink, behind a thin accent rule.
  return (
    <div style={{ ...box, display: 'flex', alignItems: 'flex-start' }}>
      <div
        style={{
          ...rise(reveal, 1.6),
          display: 'flex',
          gap: `${SPACE.sm}cqw`,
          alignItems: 'stretch',
          maxWidth: '100%',
        }}
      >
        <div
          style={{
            width: '0.45cqw',
            flexShrink: 0,
            borderRadius: '0.3cqw',
            background: withAlpha(palette.accent, 0.9),
          }}
        />
        <span style={{ ...typeStyle('body', fonts.body), color: palette.soft }}>{layer.content}</span>
      </div>
    </div>
  );
}
