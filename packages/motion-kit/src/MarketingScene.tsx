import type { MotionProp, MotionScene as MotionSceneSpec, Scene } from '@sikto/scene-kit';
import type { ReactNode } from 'react';
import { AbsoluteFill, Freeze, Img, Sequence, useCurrentFrame, useVideoConfig } from 'remotion';
import { AbstractShapes } from './AbstractShapes';
import { OutroWrap } from './OutroWrap';
import { PaperBg } from './PaperBg';
import { ParallaxRig } from './ParallaxRig';
import { StepWobble } from './StepWobble';
import { DESIGN_H, DESIGN_W, PALETTES, type MotionPalette } from './tokens';
import { BlurOutUp } from './remocn/blur-out-up';
import { Confetti } from './remocn/confetti';
import { DynamicGrid } from './remocn/dynamic-grid';
import { MeshGradientBg } from './remocn/mesh-gradient-bg';
import { RollingNumber } from './remocn/rolling-number';
import { SpringScaleIn } from './remocn/spring-scale-in';
import { StaggeredFadeUp } from './remocn/staggered-fade-up';
import { TrackingIn } from './remocn/tracking-in';

const FONT_STACK = 'Inter, Geist, system-ui, sans-serif';

/** blur-out-up exits near its sequence end; freeze it fully-entered instead
 * (the local frame is already past every word's entrance by `at`). */
function HoldAfter({ at, children }: { at: number; children: ReactNode }) {
  const local = useCurrentFrame();
  return (
    <Freeze frame={at} active={local > at}>
      {children}
    </Freeze>
  );
}

function Title({ motion, text, pal, boxPx }: { motion: MotionSceneSpec; text: string; pal: MotionPalette; boxPx: number }) {
  // fit the line in its column even at max camera zoom (~0.56em avg glyph width)
  const fontSize = Math.round(Math.min(66, Math.max(34, boxPx / (0.6 * Math.max(1, text.length)))));
  const common = { text, fontSize, color: pal.ink, fontWeight: 700 };
  // A title that is one number gets the rolling-number treatment (stat beats).
  const num = /^[\d,.]+$/.test(text.trim()) ? Number(text.replace(/[^\d.]/g, '')) : null;
  if (num !== null && Number.isFinite(num)) {
    return <RollingNumber from={0} to={num} fontSize={fontSize * 1.5} color={pal.ink} />;
  }
  switch (motion.text_style) {
    case 'blur_up':
      return (
        <HoldAfter at={17 + text.split(' ').length + 4}>
          <BlurOutUp {...common} staggerDelay={1} />
        </HoldAfter>
      );
    case 'tracking_in':
      return <TrackingIn {...common} startTracking={0.5} />;
    case 'spring_in':
      return <SpringScaleIn {...common} staggerDelay={3} />;
    default:
      return <StaggeredFadeUp {...common} staggerDelay={4} />;
  }
}

/** One prop line. The remocn text components fill+center their nearest
 * positioned ancestor, so every row is a fixed-height relative box. */
function PropRow({ prop, motion, pal, seed, index, boxPx }: { prop: MotionProp; motion: MotionSceneSpec; pal: MotionPalette; seed: string; index: number; boxPx: number }) {
  // paper background: chips/ctas read as paper cutouts with a hard offset shadow
  const cutout = motion.background === 'paper' ? '4px 5px 0 rgba(0,0,0,0.35)' : undefined;
  if (prop.role === 'chip') {
    return (
      <StepWobble seed={`${seed}:chip`}>
        <div
          style={{
            display: 'inline-block',
            padding: '8px 18px',
            borderRadius: 999,
            border: `2px solid ${pal.accent}`,
            color: pal.accent,
            fontSize: 20,
            fontWeight: 600,
            boxShadow: cutout,
          }}
        >
          {prop.content}
        </div>
      </StepWobble>
    );
  }
  if (prop.role === 'cta') {
    return (
      <StepWobble seed={`${seed}:cta`}>
        <div
          style={{
            display: 'inline-block',
            padding: '16px 34px',
            borderRadius: 14,
            background: pal.accent,
            color: pal.bg,
            fontSize: 26,
            fontWeight: 700,
            boxShadow: cutout,
          }}
        >
          {prop.content}
        </div>
      </StepWobble>
    );
  }
  if (prop.role === 'title' || prop.role === 'stat') {
    return (
      <StepWobble seed={`${seed}:title:${index}`} style={{ position: 'relative', width: '100%', height: 210 }}>
        <Title motion={motion} text={prop.content} pal={pal} boxPx={boxPx} />
      </StepWobble>
    );
  }
  // sub and anything else: quiet supporting line
  return (
    <StepWobble seed={`${seed}:sub:${index}`} style={{ position: 'relative', width: '100%', height: 80 }}>
      <StaggeredFadeUp text={prop.content} staggerDelay={4} fontSize={28} color={pal.soft} fontWeight={500} />
    </StepWobble>
  );
}

/** One marketing scene: background, parallax planes (images + set dressing),
 * a staggered text stack, an accent, and an outro — all from `scene.motion`
 * intent. Runs identically under the MP4 renderer and @remotion/player. */
export function MarketingScene({ scene, durationMs }: { scene: Scene; durationMs: number }) {
  const frame = useCurrentFrame();
  const { fps, width, height } = useVideoConfig();
  const tMs = (frame / fps) * 1000;
  const motion = scene.motion;
  if (!motion) return null;
  const pal = PALETTES[motion.palette] ?? PALETTES.midnight;
  const seed = scene.id;
  const scale = Math.min(width / DESIGN_W, height / DESIGN_H);
  const imagePlanes = (motion.planes ?? []).filter((p) => p.src);
  // pre-v2 lessons in the DB have no camera/outro — render them, don't crash
  const camera = motion.camera ?? { drift: 'right' as const, zoom: 'in' as const, tilt_deg: 0 };
  const outro = motion.outro ?? 'none';

  const layers = [
    {
      depth: 'far' as const,
      node: <AbstractShapes palette={pal} seed={seed} depth="far" />,
    },
    ...imagePlanes.map((p) => ({
      depth: p.depth,
      node: (
        <div
          style={{
            position: 'absolute' as const,
            right: '6%',
            top: '16%',
            width: p.depth === 'near' ? 380 : 460,
            height: p.depth === 'near' ? 300 : 340,
            borderRadius: 18,
            overflow: 'hidden',
            border: `1px solid ${pal.bg2}`,
            boxShadow: '0 18px 50px rgba(0,0,0,0.35)',
          }}
        >
          <Img src={p.src!} style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
        </div>
      ),
    })),
    {
      depth: 'near' as const,
      node: <AbstractShapes palette={pal} seed={`${seed}:n`} depth="near" />,
    },
  ];

  return (
    <AbsoluteFill style={{ background: pal.bg }}>
      <div
        style={{
          position: 'absolute',
          left: '50%',
          top: '50%',
          width: DESIGN_W,
          height: DESIGN_H,
          transform: `translate(-50%, -50%) scale(${scale.toFixed(4)})`,
          fontFamily: FONT_STACK,
          overflow: 'hidden',
        }}
      >
        <OutroWrap outro={outro} tMs={tMs} durationMs={durationMs}>
          {motion.background === 'mesh' ? (
            <MeshGradientBg colors={[...pal.mesh]} background={pal.bg} />
          ) : motion.background === 'grid' ? (
            <DynamicGrid cellSize={40} lineColor={pal.bg2} background={pal.bg} />
          ) : motion.background === 'paper' ? (
            <PaperBg palette={pal} seed={seed} />
          ) : null}
          <ParallaxRig camera={camera} tMs={tMs} durationMs={durationMs} layers={layers}>
            <div
              style={{
                position: 'absolute',
                left: '8%',
                top: '50%',
                transform: 'translateY(-50%)',
                width: imagePlanes.length ? '50%' : '72%',
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                gap: 18,
              }}
            >
              {motion.props.map((prop, i) => (
                <Sequence key={i} from={i * 12} layout="none">
                  <PropRow
                    prop={prop}
                    motion={motion}
                    pal={pal}
                    seed={seed}
                    index={i}
                    boxPx={DESIGN_W * (imagePlanes.length ? 0.5 : 0.72)}
                  />
                </Sequence>
              ))}
            </div>
          </ParallaxRig>
          {motion.accent === 'confetti' ? <Confetti particleCount={120} colors={[pal.accent, pal.ink, pal.soft]} /> : null}
          {motion.accent === 'sparks' ? <Confetti particleCount={40} colors={[pal.accent]} /> : null}
        </OutroWrap>
      </div>
    </AbsoluteFill>
  );
}
