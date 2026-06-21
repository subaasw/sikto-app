'use client';

import { SceneBackground } from '@sikto/scene-kit';
import type { BackgroundStyle, SceneTheme } from '@/lib/scene/types';

const THEME: SceneTheme = {
  primary: '#84cc16',
  background: '#0c0e08',
  foreground: '#edf2e2',
  font: 'Geist',
};

/** Preview tile for one background style, rendered via the shared engine. */
export function BackgroundTile({ style }: { style: BackgroundStyle }) {
  return (
    <div
      className="relative aspect-video w-full overflow-hidden border-2 border-border"
      style={{ containerType: 'inline-size' }}
    >
      <SceneBackground theme={{ ...THEME, background_style: style }} progressMs={3000} />
    </div>
  );
}
