import { DEFAULT_SCENE_MS, MIN_SCENE_MS, type Scene, type SceneAudio, type SceneDocument } from './types';

export function audioById(audio: SceneAudio[]): Record<string, SceneAudio> {
  return Object.fromEntries(audio.map((a) => [a.scene_id, a]));
}

/** A scene's on-screen duration: its narration audio when known, else its own
 * `duration_ms`, else a default. `audioByScene` is optional (the live player may
 * estimate narration length separately). */
export function sceneDurationMs(
  scene: Scene,
  audioByScene: Record<string, SceneAudio> = {},
): number {
  const audio = audioByScene[scene.id];
  const ms = audio?.duration_ms ?? scene.duration_ms ?? DEFAULT_SCENE_MS;
  return Math.max(MIN_SCENE_MS, ms);
}

export function totalDurationMs(
  document: SceneDocument,
  audioByScene: Record<string, SceneAudio> = {},
): number {
  return document.scenes.reduce((sum, scene) => sum + sceneDurationMs(scene, audioByScene), 0);
}

/** Rough spoken-duration estimate (~165 wpm) for live narration with no audio. */
export function estimateNarrationMs(text: string): number {
  const words = text.trim().split(/\s+/).filter(Boolean).length;
  return Math.max(2500, Math.round((words / 165) * 60_000));
}

/** Cumulative start time (ms) of each scene, plus the total. */
export function offsetsFrom(durations: number[]): { offsets: number[]; total: number } {
  const offsets: number[] = [];
  let acc = 0;
  for (const d of durations) {
    offsets.push(acc);
    acc += d;
  }
  return { offsets, total: acc };
}

/** Which scene a global playhead falls in, and the local ms within that scene. */
export function locate(
  offsets: number[],
  total: number,
  ms: number,
): { index: number; localMs: number } {
  let index = 0;
  for (let i = 0; i < offsets.length; i++) {
    if (ms >= offsets[i]) index = i;
  }
  return { index, localMs: Math.min(ms - offsets[index], total - offsets[index]) };
}
