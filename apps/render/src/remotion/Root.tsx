import { Composition, type CalculateMetadataFunction } from 'remotion';
import { Lesson } from './Lesson';
import {
  audioById,
  DIMENSIONS,
  FPS,
  sceneDurationMs,
  type LessonProps,
  type SceneDocument,
} from './schema';

const EMPTY_DOCUMENT: SceneDocument = {
  version: 1,
  title: 'Lesson',
  summary: '',
  aspect_ratio: '16:9',
  theme: { primary: '#84cc16', background: '#0c0e08', foreground: '#edf2e2', font: 'Geist' },
  scenes: [
    {
      id: 's0',
      kind: 'slide',
      narration: { text: '' },
      elements: [],
      animations: [],
      manim_entry: 'MainScene',
    },
  ],
};

const DEFAULT_PROPS: LessonProps = { document: EMPTY_DOCUMENT, audio: [], manim_clips: {} };

const calculateMetadata: CalculateMetadataFunction<LessonProps> = ({ props }) => {
  const audioByScene = audioById(props.audio);
  const [width, height] = DIMENSIONS[props.document.aspect_ratio];
  const totalMs = props.document.scenes.reduce(
    (sum, scene) => sum + sceneDurationMs(scene, audioByScene),
    0,
  );
  return {
    durationInFrames: Math.max(1, Math.round((totalMs / 1000) * FPS)),
    fps: FPS,
    width,
    height,
  };
};

export const RemotionRoot = () => (
  <Composition
    id="Lesson"
    component={Lesson}
    durationInFrames={FPS * 4}
    fps={FPS}
    width={1920}
    height={1080}
    defaultProps={DEFAULT_PROPS}
    calculateMetadata={calculateMetadata}
  />
);
