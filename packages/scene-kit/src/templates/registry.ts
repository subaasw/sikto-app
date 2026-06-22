import type { SceneTheme } from '../types';
import { explainer } from './explainer';
import { marketing } from './marketing';
import type { TemplateModule } from './types';
import { whiteboard } from './whiteboard';

const BY_ID: Record<string, TemplateModule> = { explainer, marketing, whiteboard };

/**
 * Pick the render module for a theme. Prefers the explicit `template` id; falls
 * back to inferring from capability flags (for documents generated before the
 * id existed), then to explainer.
 */
export function getTemplate(theme: SceneTheme): TemplateModule {
  if (theme.template && BY_ID[theme.template]) return BY_ID[theme.template];
  if (
    theme.element_style === 'sticker' ||
    theme.background_style === 'texture' ||
    theme.motion === 'punchy'
  ) {
    return marketing;
  }
  if (theme.sketch || theme.motion === 'sketch' || theme.background_style === 'grid') {
    return whiteboard;
  }
  return explainer;
}
