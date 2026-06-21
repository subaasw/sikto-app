'use client';

import { SceneStage } from '@sikto/scene-kit';
import type { Scene, SceneTheme } from '@/lib/scene/types';

// A static sample scene used to preview a template's look.
function sampleScene(): Scene {
  const bullet = (id: string, text: string): Scene['elements'][number] => ({
    id,
    type: 'bullets',
    items: [text],
    frame: { x: 0.08, y: 0, w: 0.84, h: 0.12 },
    z: 0,
  });
  return {
    id: 'preview',
    kind: 'slide',
    narration: { text: '' },
    manim_entry: 'MainScene',
    elements: [
      {
        id: 'h',
        type: 'heading',
        text: 'How it works',
        frame: { x: 0.08, y: 0.22, w: 0.84, h: 0.18 },
        z: 0,
        emphasis: ['works'],
      },
      { ...bullet('b0', 'Grounded in your source'), frame: { x: 0.08, y: 0.46, w: 0.84, h: 0.12 } },
      { ...bullet('b1', 'Narrated step by step'), frame: { x: 0.08, y: 0.62, w: 0.84, h: 0.12 } },
      { ...bullet('b2', 'Rendered to video'), frame: { x: 0.08, y: 0.78, w: 0.84, h: 0.12 } },
    ],
    animations: [
      { target_id: 'h', type: 'fade-in', at_ms: 0, duration_ms: 1 },
      { target_id: 'b0', type: 'reveal', at_ms: 0, duration_ms: 1 },
      { target_id: 'b1', type: 'reveal', at_ms: 0, duration_ms: 1 },
      { target_id: 'b2', type: 'reveal', at_ms: 0, duration_ms: 1 },
    ],
  };
}

const SCENE = sampleScene();

/** A small 16:9 preview of how a theme/template renders, via the shared engine. */
export function ScenePreview({ theme }: { theme: SceneTheme }) {
  return (
    <div className="relative w-full overflow-hidden border-2 border-border" style={{ aspectRatio: '16 / 9' }}>
      <SceneStage scene={SCENE} theme={theme} progressMs={9_999_999} sceneDurationMs={4000} />
    </div>
  );
}
