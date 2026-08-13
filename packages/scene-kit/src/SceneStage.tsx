import type { CSSProperties } from 'react';
import { TYPE_SCALE, resolveTokens } from './tokens';
import { CleanLayerView } from './CleanLayerView';
import { DiagramView } from './DiagramView';
import { Hand } from './Hand';
import { LayerView } from './LayerView';
import { renderBackground } from './templates/backgrounds';
import { DEFAULT_SCENE_MS, type ImgComponent, type Layer, type RenderProfile, type Scene, type SceneTheme, type WordTiming } from './types';
import { drawWindows, revealFor, WhiteboardSheet } from './whiteboard';

/** Teaching order in which layers are drawn on: title first, then the visual,
 * then supporting captions. Independent of paint depth. */
function drawRank(l: Layer): number {
  if (l.kind === 'headline') return 0;
  if (l.kind === 'image' || l.kind === 'shape') return 1;
  return 2; // caption, sticker
}

/**
 * Renders one scene — the single source of truth shared by the live player and
 * the Remotion exporter, so preview == MP4.
 *
 * A slide scene is a whiteboard: a light board onto which `layers` are drawn on
 * one at a time (in teaching order) by a hand+marker, then held. A manim scene
 * plays its rendered clip.
 *
 * - `progressMs`: elapsed time within the scene (player clock; Remotion passes
 *   `frame / fps * 1000`).
 * - `sceneDurationMs`: drives the draw pacing so the board fills over the scene.
 */
export function SceneStage({
  scene,
  theme,
  progressMs,
  sceneDurationMs,
  Img,
  Video,
  manimUrl,
}: {
  scene: Scene;
  theme: SceneTheme;
  progressMs: number;
  sceneDurationMs?: number;
  // accepted for call-site compatibility; the whiteboard renderer doesn't use these
  revealCount?: number;
  words?: WordTiming[];
  profile?: RenderProfile;
  Img?: ImgComponent;
  Video?: ImgComponent; // host video component (Remotion OffthreadVideo / plain <video>)
  manimUrl?: string; // rendered Manim clip for this scene
}) {
  const tokens = resolveTokens(theme);
  const container: CSSProperties = {
    position: 'absolute',
    inset: 0,
    containerType: 'inline-size',
    color: tokens.palette.ink,
    fontFamily: tokens.fonts.body,
  };

  if (scene.kind === 'manim') {
    if (manimUrl && Video) {
      return (
        <div style={{ ...container, background: scene.background ?? tokens.palette.bg }}>
          <Video src={manimUrl} style={{ width: '100%', height: '100%', objectFit: 'contain' }} />
        </div>
      );
    }
    return (
      <div
        style={{
          ...container,
          background: scene.background ?? tokens.palette.bg,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          textAlign: 'center',
          padding: '8%',
        }}
      >
        <div style={{ fontSize: `${TYPE_SCALE.body.size}cqw`, opacity: 0.85 }}>
          {scene.narration.caption ?? scene.narration.text}
        </div>
      </div>
    );
  }

  // motion scenes render through @sikto/motion-kit (both hosts branch before
  // SceneStage); an unhandled one falls through to the whiteboard below.

  if (scene.kind === 'diagram') {
    return (
      <div style={{ ...container, background: scene.background ?? tokens.palette.bg }}>
        <DiagramView
          elements={scene.elements}
          theme={theme}
          progressMs={progressMs}
          sceneDurationMs={sceneDurationMs}
        />
      </div>
    );
  }

  // Whiteboard: the board, then each drawable layer wiped on in teaching order.
  const drawable = (scene.layers ?? [])
    .filter((l) => l.kind !== 'bg-texture')
    .sort((a, b) => drawRank(a) - drawRank(b));
  const windows = drawWindows(drawable.length, sceneDurationMs ?? DEFAULT_SCENE_MS);

  // Clean (non-sketch) templates — explainer & friends — get the professional
  // renderer: layers fade/rise in over a solid background, no marker hand.
  if (!theme.sketch) {
    return (
      <div style={container}>
        {renderBackground(theme, progressMs)}
        {drawable.map((layer, i) => (
          <CleanLayerView
            key={i}
            layer={layer}
            theme={theme}
            reveal={revealFor(progressMs, windows[i])}
            Img={Img}
          />
        ))}
      </div>
    );
  }

  // The hand rides the wipe edge of whichever layer is currently drawing.
  const activeIndex = windows.findIndex((w) => progressMs > w.start && progressMs < w.end);
  let hand: { x: number; y: number } | null = null;
  if (activeIndex >= 0) {
    const layer = drawable[activeIndex];
    const f = layer.frame;
    if (f) {
      const reveal = revealFor(progressMs, windows[activeIndex]);
      hand = { x: (f.x + reveal * f.w) * 100, y: (f.y + f.h * 0.5) * 100 };
    }
  }

  // The board frame draws itself in over the scene's first ~12%, before content.
  const dur = sceneDurationMs ?? DEFAULT_SCENE_MS;
  const boardReveal = Math.max(0, Math.min(1, progressMs / (dur * 0.12)));

  return (
    <div style={container}>
      <WhiteboardSheet theme={theme} reveal={boardReveal} />
      {drawable.map((layer, i) => (
        <LayerView key={i} layer={layer} theme={theme} reveal={revealFor(progressMs, windows[i])} Img={Img} />
      ))}
      {hand && <Hand x={hand.x} y={hand.y} color={tokens.palette.accent} />}
    </div>
  );
}
