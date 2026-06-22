import type { SceneTheme } from './types';
import { renderBackground } from './templates/backgrounds';

/**
 * The scene's background layer, chosen by the theme's `background_style`. Driven
 * by `progressMs` so motion is identical in the live player and the Remotion
 * render. (Per-template entrance motion / element treatment live in the template
 * modules; the background is an orthogonal knob.)
 */
export function SceneBackground({
  theme,
  progressMs,
}: {
  theme: SceneTheme;
  progressMs: number;
}) {
  return renderBackground(theme, progressMs);
}
