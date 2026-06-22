import type { SceneTheme } from './types';
import { getTemplate } from './templates/registry';

/**
 * The scene's background layer — delegates to the active template module so each
 * template owns its own look (see templates/<name>.tsx). Driven by `progressMs`
 * so motion is identical in the live player and the Remotion render.
 */
export function SceneBackground({
  theme,
  progressMs,
}: {
  theme: SceneTheme;
  progressMs: number;
}) {
  return getTemplate(theme).Background({ theme, progressMs });
}
