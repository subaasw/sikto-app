import type { CSSProperties, ReactElement } from 'react';
import type { Animation, Element, RenderProfile, SceneTheme, WordTiming } from '../types';

/** Inputs an entrance needs to compute an element's per-frame style. */
export interface EntranceCtx {
  element: Element;
  anim: Animation;
  atMs: number; // when this element's entrance starts
  progressMs: number; // elapsed time in the scene
  index: number; // reveal order — lets a template vary motion per element
  profile: RenderProfile;
  words?: WordTiming[]; // narration timings — lets motion sync to the voice
}

/** Optional per-element visual treatment (e.g. marketing's sticker frame). */
export interface ElementTreatment {
  wrapStyle?: CSSProperties; // merged into the element's frame box
  imageObjectFit?: 'cover' | 'contain';
}

/**
 * One template = one self-contained look + motion. Each lives in its own file
 * so its background, entrance motion, and element treatment read top-to-bottom
 * instead of being scattered across shared `if/else` blocks.
 */
export interface TemplateModule {
  id: string;
  Background: (props: { theme: SceneTheme; progressMs: number }) => ReactElement;
  entrance: (ctx: EntranceCtx) => CSSProperties;
  elementTreatment?: (element: Element, theme: SceneTheme) => ElementTreatment;
}
