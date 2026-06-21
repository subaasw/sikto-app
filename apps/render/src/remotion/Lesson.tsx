import { Captions, SceneStage } from '@sikto/scene-kit';
import { linearTiming, TransitionSeries } from '@remotion/transitions';
import { fade } from '@remotion/transitions/fade';
import {
  AbsoluteFill,
  Audio,
  Img,
  OffthreadVideo,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from 'remotion';
import {
  audioById,
  sceneDurationMs,
  type LessonProps,
  type Scene,
  type SceneTheme,
  type WordTiming,
} from './schema';

// Frames the crossfade between scenes lasts (subtle).
const TRANSITION_FRAMES = 12;

/** One scene, time-driven by the Remotion frame clock and rendered through the
 * shared SceneStage so the MP4 matches the live player exactly. */
// Remotion's OffthreadVideo expects `src`; adapt it to scene-kit's
// `{ src, style }` injectable video component.
function ManimVideo({ src, style }: { src: string; style?: React.CSSProperties }) {
  // The worker wrote clips into the bundle's public dir; resolve the relative
  // path via staticFile (data-URLs overflow OffthreadVideo's proxy → HTTP 431).
  const resolved = /^(https?:|data:|blob:)/.test(src) ? src : staticFile(src);
  return <OffthreadVideo src={resolved} style={style} muted />;
}

function RenderedScene({
  scene,
  theme,
  durationMs,
  words,
  profile,
  manimUrl,
}: {
  scene: Scene;
  theme: SceneTheme;
  durationMs: number;
  words?: WordTiming[];
  profile?: 'slide' | 'video';
  manimUrl?: string;
}) {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const progressMs = (frame / fps) * 1000;
  return (
    <>
      <SceneStage scene={scene} theme={theme} progressMs={progressMs} sceneDurationMs={durationMs} words={words} profile={profile} Img={Img} Video={ManimVideo} manimUrl={manimUrl} />
      <Captions words={words} progressMs={progressMs} theme={theme} />
    </>
  );
}

export function Lesson({ document, audio, manim_clips }: LessonProps) {
  const { fps } = useVideoConfig();
  const audioByScene = audioById(audio);
  const scenes = document.scenes;

  return (
    <AbsoluteFill style={{ background: document.theme.background }}>
      <TransitionSeries>
        {scenes.flatMap((scene, i) => {
          const durationMs = sceneDurationMs(scene, audioByScene);
          const durationInFrames = Math.max(1, Math.round((durationMs / 1000) * fps));
          const track = audioByScene[scene.id];
          const sequence = (
            <TransitionSeries.Sequence key={scene.id} durationInFrames={durationInFrames}>
              <RenderedScene
                scene={scene}
                theme={document.theme}
                durationMs={durationMs}
                words={track?.words}
                profile={document.profile}
                manimUrl={manim_clips?.[scene.id]}
              />
              {track ? <Audio src={track.url} /> : null}
            </TransitionSeries.Sequence>
          );
          // A subtle crossfade between consecutive scenes.
          if (i === 0) return [sequence];
          return [
            <TransitionSeries.Transition
              key={`${scene.id}-t`}
              presentation={fade()}
              timing={linearTiming({ durationInFrames: TRANSITION_FRAMES })}
            />,
            sequence,
          ];
        })}
      </TransitionSeries>
    </AbsoluteFill>
  );
}
