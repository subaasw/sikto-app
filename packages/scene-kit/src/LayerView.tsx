import type { CSSProperties } from 'react';
import type { ImgComponent, Layer, SceneTheme } from './types';
import { STROKE, TYPE_SCALE, resolveTokens, withAlpha } from './tokens';
import { wipeMask } from './whiteboard';
import { Sketch, seedFrom, wobblyLine, wobblyRect } from './sketch';

// One drawable layer on the whiteboard. Everything is rendered as if a hand laid
// it down: text is WRITTEN in the script font (revealed left-to-right so it
// reads as writing), the headline gets a marker underline, key terms get circled
// in the SECOND marker (real boards use two markers), and illustrations are
// wiped in inside a sketched frame. `reveal` (0..1) is the draw clock for this
// layer — the same value drives the wipe and the strokes so ink, underline, and
// the SceneStage hand all advance together.

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

export function LayerView({
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
  const seed = seedFrom((layer.content ?? '') + layer.kind + layer.region);

  // Illustration: wiped on inside a hand-drawn frame. The marker-hand (SceneStage)
  // rides the wipe edge, so it reads as the hand sketching it in. `contain` shows
  // the whole drawing (a whiteboard sketch isn't cropped).
  if (layer.kind === 'image') {
    if (!layer.content || !Img) return null;
    return (
      <div style={box}>
        <div style={{ position: 'relative', width: '100%', height: '100%' }}>
          <Img
            src={layer.content}
            style={{ width: '100%', height: '100%', objectFit: 'contain', ...wipeMask(reveal) }}
          />
          <Sketch d={wobblyRect(seed, 1.4)} reveal={reveal} color={withAlpha(palette.ink, 0.33)} width={STROKE.line} />
        </div>
      </div>
    );
  }

  // A drawn accent rule.
  if (layer.kind === 'shape') {
    return (
      <div style={box}>
        <div style={{ position: 'absolute', left: 0, right: 0, top: '45%', height: '2.4cqw' }}>
          <Sketch d={wobblyLine(seed, 6, 1.4)} reveal={reveal} color={palette.accent} width={STROKE.marker} viewBox="0 0 100 12" />
        </div>
      </div>
    );
  }

  if (!layer.content) return null;

  // A circled keyword — the second marker, so emphasis reads differently from headings.
  if (layer.kind === 'sticker') {
    return (
      <div style={{ ...box, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <span style={{ position: 'relative', padding: '1cqw 2.2cqw', display: 'inline-block' }}>
          <span
            style={{
              fontFamily: fonts.script,
              fontWeight: 700,
              fontSize: '4.4cqw',
              color: palette.accent2,
              lineHeight: 1.15,
              ...wipeMask(reveal),
            }}
          >
            {layer.content}
          </span>
          <Sketch d={wobblyRect(seed, 2)} reveal={reveal} color={palette.accent2} width={2.5} />
        </span>
      </div>
    );
  }

  // headline / caption: script, written in left-to-right; the headline gets a
  // marker underline drawn on under it.
  const isHead = layer.kind === 'headline';
  const spec = isHead ? TYPE_SCALE.scriptHead : TYPE_SCALE.scriptBody;
  return (
    <div style={{ ...box, display: 'flex', alignItems: 'flex-start', justifyContent: 'flex-start' }}>
      <div style={{ position: 'relative', maxWidth: '100%' }}>
        <span
          style={{
            fontFamily: fonts.script,
            fontWeight: spec.weight,
            fontSize: `${spec.size}cqw`,
            color: palette.ink,
            lineHeight: spec.lineHeight,
            display: 'inline-block',
            ...wipeMask(reveal),
          }}
        >
          {layer.content}
        </span>
        {isHead && (
          <div style={{ position: 'absolute', left: 0, right: '-2%', bottom: '-2.6cqw', height: '2.6cqw' }}>
            <Sketch d={wobblyLine(seed, 6, 1.8)} reveal={reveal} color={palette.accent} width={3.5} viewBox="0 0 100 12" />
          </div>
        )}
      </div>
    </div>
  );
}
