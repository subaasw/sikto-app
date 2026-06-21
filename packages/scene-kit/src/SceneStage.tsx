import type { CSSProperties } from 'react';
import { ElementView, type ImgComponent } from './ElementView';
import { appearance, clamp } from './motion';
import { SceneBackground } from './SceneBackground';
import { SceneDecor } from './SceneDecor';
import type { Animation, Frame, MotionStyle, RenderProfile, Scene, SceneTheme, WordTiming } from './types';

function frameStyle(frame: Frame): CSSProperties {
  return {
    position: 'absolute',
    left: `${frame.x * 100}%`,
    top: `${frame.y * 100}%`,
    width: `${frame.w * 100}%`,
    height: `${frame.h * 100}%`,
    display: 'flex',
    flexDirection: 'column',
    justifyContent: 'center',
    overflow: 'hidden', // never let an element spill its frame
  };
}

/**
 * Renders one scene. This is the single source of truth for how a scene looks —
 * the live player and the Remotion exporter both render through it, so the video
 * and the in-browser preview are always identical.
 *
 * - `progressMs`: elapsed time within the scene. The player passes its clock;
 *   Remotion passes `frame / fps * 1000`.
 * - `sceneDurationMs`: the scene's full length (its narration). When given, the
 *   element reveals are spread across the narration so the visuals build as the
 *   voice-over speaks — instead of all firing in the first second.
 * - `revealCount` (class/step-through mode): show only the first N animated
 *   elements (by reveal order) instead of gating by time.
 *
 * The root sets a container so `cqw` units resolve to the stage width in any host.
 */
export function SceneStage({
  scene,
  theme,
  progressMs,
  sceneDurationMs,
  revealCount,
  words,
  profile = 'video',
  Img,
  Video,
  manimUrl,
}: {
  scene: Scene;
  theme: SceneTheme;
  progressMs: number;
  sceneDurationMs?: number;
  revealCount?: number;
  words?: WordTiming[];
  profile?: RenderProfile;
  Img?: ImgComponent;
  Video?: ImgComponent; // host video component (Remotion OffthreadVideo / plain <video>)
  manimUrl?: string; // rendered Manim clip for this scene
}) {
  const motion: MotionStyle = theme.motion ?? 'smooth';
  const container: CSSProperties = {
    position: 'absolute',
    inset: 0,
    containerType: 'inline-size',
    color: theme.foreground,
    fontFamily: theme.font,
  };

  if (scene.kind === 'manim') {
    // Play the rendered Manim clip if we have one + a host video component;
    // otherwise fall back to the narration text stub.
    if (manimUrl && Video) {
      return (
        <div style={{ ...container, background: scene.background ?? theme.background }}>
          <Video src={manimUrl} style={{ width: '100%', height: '100%', objectFit: 'contain' }} />
        </div>
      );
    }
    return (
      <div
        style={{
          ...container,
          background: scene.background ?? theme.background,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          textAlign: 'center',
          padding: '8%',
        }}
      >
        <div style={{ fontSize: '2.6cqw', opacity: 0.85 }}>
          {scene.narration.caption ?? scene.narration.text}
        </div>
      </div>
    );
  }

  const animFor: Record<string, Animation> = Object.fromEntries(
    scene.animations.map((a) => [a.target_id, a]),
  );
  const orderOf: Record<string, number> = Object.fromEntries(
    scene.animations.map((a, i) => [a.target_id, i]),
  );
  const steps = scene.animations.length;

  // When the scene's full length is known, spread reveals across the first
  // ~62% of the narration so each point lands as it's spoken; otherwise fall
  // back to each animation's authored `at_ms`.
  function startMs(anim: Animation, idx: number): number {
    if (sceneDurationMs && steps > 0) return (idx / steps) * sceneDurationMs * 0.62;
    return anim.at_ms;
  }

  function styleFor(id: string): CSSProperties {
    const anim = animFor[id];
    const ord = orderOf[id];
    if (revealCount === undefined) {
      if (!anim) return { opacity: 1 };
      // A "draw" element stays mounted at full opacity; its draw progress (below)
      // is the reveal, not a fade.
      if (anim.type === 'draw') return { opacity: 1 };
      return appearance(anim, startMs(anim, ord ?? 0), progressMs, motion, profile);
    }
    const shown = ord === undefined || ord < revealCount;
    return shown
      ? { opacity: 1, transition: 'opacity 250ms ease, transform 250ms ease' }
      : { opacity: 0, transform: 'translateY(12px)' };
  }

  // 0..1 reveal progress for an element — drives "draw" elements (and is safe to
  // pass to any element; non-drawn ones ignore it).
  function progressFor(id: string): number {
    const anim = animFor[id];
    const ord = orderOf[id];
    if (revealCount !== undefined) return ord === undefined || ord < revealCount ? 1 : 0;
    if (!anim) return 1;
    const ratio = (progressMs - startMs(anim, ord ?? 0)) / Math.max(1, anim.duration_ms);
    return Number.isFinite(ratio) ? clamp(ratio, 0, 1) : 1;
  }

  return (
    <div style={{ ...container, background: scene.background ?? theme.background, padding: '4%' }}>
      {scene.background ? null : <SceneBackground theme={theme} progressMs={progressMs} />}
      {scene.elements.map((element) => (
        <div key={element.id} style={{ ...frameStyle(element.frame), ...styleFor(element.id) }}>
          <ElementView
            element={element}
            theme={theme}
            progress={progressFor(element.id)}
            progressMs={progressMs}
            words={words}
            Img={Img}
          />
        </div>
      ))}
      {revealCount === undefined ? (
        <SceneDecor theme={theme} progressMs={progressMs} sceneDurationMs={sceneDurationMs} />
      ) : null}
    </div>
  );
}
