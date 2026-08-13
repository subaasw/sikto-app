import { MarketingScene } from '@sikto/motion-kit';
import { Captions, SceneStage } from '@sikto/scene-kit';
import {
  AbsoluteFill,
  Audio,
  Img,
  OffthreadVideo,
  Series,
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
  if (scene.kind === 'motion' && scene.motion) {
    // marketing copy IS the on-screen text — no captions overlay
    return <MarketingScene scene={scene} durationMs={durationMs} />;
  }
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
      <Series>
        {scenes.map((scene) => {
          const durationMs = sceneDurationMs(scene, audioByScene);
          const durationInFrames = Math.max(1, Math.round((durationMs / 1000) * fps));
          const track = audioByScene[scene.id];
          return (
            <Series.Sequence key={scene.id} durationInFrames={durationInFrames}>
              <RenderedScene
                scene={scene}
                theme={document.theme}
                durationMs={durationMs}
                words={track?.words}
                profile={document.profile}
                manimUrl={manim_clips?.[scene.id]}
              />
              {track ? <Audio src={track.url} /> : null}
            </Series.Sequence>
          );
        })}
      </Series>
    </AbsoluteFill>
  );
}
