// The canonical declarative scene spec, shared by the live player (apps/web)
// and the Remotion exporter (apps/render). Field names are snake_case to match
// the JSON the FastAPI backend returns verbatim (api/scenes/schema.py).

export type ElementType =
  | 'heading'
  | 'text'
  | 'bullets'
  | 'latex'
  | 'image'
  | 'shape'
  | 'code'
  | 'card'
  | 'character';

export interface Frame {
  x: number;
  y: number;
  w: number;
  h: number;
}

/** Host-supplied image/video component (Remotion <Img>/<OffthreadVideo> in the
 * exporter, plain tags in the live player). */
export type ImgComponent = import('react').ComponentType<{
  src: string;
  style?: import('react').CSSProperties;
  alt?: string;
}>;

export interface Element {
  id: string;
  type: ElementType;
  frame: Frame;
  z: number;
  text?: string | null;
  items?: string[] | null;
  latex?: string | null;
  src?: string | null;
  shape?: 'rect' | 'ellipse' | 'line' | 'arrow' | null;
  emphasis?: string[] | null;
  style?: Record<string, unknown>;
}

/** @deprecated use {@link Element} — kept so apps/web imports keep resolving. */
export type SceneElement = Element;

export type AnimationType = 'fade-in' | 'reveal' | 'spotlight' | 'pointer' | 'draw';

export interface Animation {
  target_id: string;
  type: AnimationType;
  at_ms: number;
  duration_ms: number;
}

/** @deprecated use {@link Animation}. */
export type SceneAnimation = Animation;

// --- Layer model (stop-motion renderer) ------------------------------------
// A slide scene is a back-to-front stack of semantic layers. The LLM composes
// them; the layout solver fills each `frame`. Mirrors api/scenes/schema.py.
export type LayerKind = 'image' | 'headline' | 'caption' | 'sticker' | 'shape' | 'bg-texture';
export type Region =
  | 'full-bleed'
  | 'left'
  | 'right'
  | 'center'
  | 'upper'
  | 'lower'
  | 'upper-third'
  | 'lower-third';
export type LayerSize = 'sm' | 'md' | 'lg' | 'full';
export type LayerMotion = 'pop' | 'drift' | 'settle' | 'none';

export interface Layer {
  kind: LayerKind;
  content?: string | null;
  region: Region;
  size: LayerSize;
  depth: number;
  motion: LayerMotion;
  frame?: Frame | null;
}

export interface Narration {
  text: string;
  caption?: string | null;
}

export type SceneKind = 'slide' | 'manim' | 'diagram' | 'motion';

// --- marketing motion engine: intent (not pixels). Mirrors api/scenes/schema.py. ---
export type MotionBeat = 'hook' | 'brand' | 'feature' | 'benefit' | 'stat' | 'social_proof' | 'cta';
export type MotionMood = 'energetic' | 'bold' | 'playful' | 'calm';
export type MotionRole = 'title' | 'sub' | 'chip' | 'icon' | 'stat' | 'cta';
export type MotionEntrance = 'drop' | 'pop' | 'fly_in' | 'rise' | 'scatter';
export type MotionAccent = 'confetti' | 'sparks' | 'none';
export type MotionPaletteName = 'midnight' | 'sunset' | 'forest' | 'royal' | 'ember' | 'slate';
export type MotionTextStyle = 'blur_up' | 'fade_up' | 'tracking_in' | 'spring_in';
export type MotionBackground = 'mesh' | 'grid' | 'paper' | 'none';
export type MotionOutro = 'wipe' | 'push' | 'frosted' | 'none';
export type CameraDrift = 'left' | 'right' | 'up' | 'down' | 'none';
export type CameraZoom = 'in' | 'out' | 'none';
export type PlaneDepth = 'far' | 'mid' | 'near';

export interface MotionCamera {
  drift: CameraDrift;
  zoom: CameraZoom;
  tilt_deg: number;
}

export interface MotionPlane {
  query: string;
  depth: PlaneDepth;
  src?: string | null;
}

export interface MotionProp {
  content: string;
  role: MotionRole;
  emphasis: number; // 0..2
  entrance: MotionEntrance;
}

export interface MotionScene {
  beat: MotionBeat;
  mood: MotionMood;
  props: MotionProp[];
  accent: MotionAccent;
  palette: MotionPaletteName;
  text_style: MotionTextStyle;
  background: MotionBackground;
  outro: MotionOutro;
  camera: MotionCamera;
  planes: MotionPlane[];
}

export interface Scene {
  id: string;
  kind: SceneKind;
  duration_ms?: number | null;
  background?: string | null;
  narration: Narration;
  elements: Element[];
  animations: Animation[];
  layers?: Layer[];
  manim_code?: string | null;
  manim_entry: string;
  motion?: MotionScene | null;
}

export type BackgroundStyle = 'gradient' | 'mesh' | 'grid' | 'solid' | 'texture';

/** Entrance/motion language for a template. */
export type MotionStyle = 'smooth' | 'punchy' | 'sketch';

/** Viewing profile: a restrained "slide" (study/pause) vs a fully animated "video". */
export type RenderProfile = 'slide' | 'video';

export interface SceneTheme {
  primary: string;
  background: string;
  foreground: string;
  font: string;
  /** Role-based palette (see tokens.ts). Optional: legacy trio still works. */
  palette?: Partial<import('./tokens').Palette> | null;
  fonts?: import('./tokens').FontSet | null;
  texture?: import('./tokens').Texture | null;
  template?: string; // template id — picks the render module (see templates/registry)
  background_style?: BackgroundStyle;
  element_style?: 'plain' | 'sticker'; // 'sticker' = cut-out border + shadow (marketing)
  sketch?: boolean; // hand-drawn (Rough.js) shapes/connectors — the whiteboard look
  motion?: MotionStyle; // how elements enter (set per template)
}

export type AspectRatio = '16:9' | '9:16' | '1:1';

export interface SceneDocument {
  version: number;
  title: string;
  summary: string;
  aspect_ratio: AspectRatio;
  theme: SceneTheme;
  scenes: Scene[];
  profile?: RenderProfile; // slide (course) vs video — set from the lesson mode
}

// --- render / playback inputs ----------------------------------------------

export interface WordTiming {
  text: string;
  start_ms: number;
  end_ms: number;
}

export interface SceneAudio {
  scene_id: string;
  url: string;
  duration_ms: number;
  words?: WordTiming[];
}

export type LessonProps = {
  document: SceneDocument;
  audio: SceneAudio[];
  /** sceneId -> rendered clip URL. Legacy/unused; kept for prop-shape stability. */
  manim_clips: Record<string, string>;
};

export const FPS = 30;
export const DEFAULT_SCENE_MS = 4000;
export const MIN_SCENE_MS = 1500;

export const DIMENSIONS: Record<AspectRatio, [number, number]> = {
  '16:9': [1920, 1080],
  '9:16': [1080, 1920],
  '1:1': [1080, 1080],
};

export const ASPECT_RATIO_CSS: Record<AspectRatio, string> = {
  '16:9': '16 / 9',
  '9:16': '9 / 16',
  '1:1': '1 / 1',
};
