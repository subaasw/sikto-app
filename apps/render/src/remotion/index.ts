import { loadFont as loadArchivoBlack } from '@remotion/google-fonts/ArchivoBlack';
import { loadFont as loadBricolage } from '@remotion/google-fonts/BricolageGrotesque';
import { loadFont as loadCaveat } from '@remotion/google-fonts/Caveat';
import { loadFont as loadGeist } from '@remotion/google-fonts/Geist';
import { registerRoot } from 'remotion';
import { RemotionRoot } from './Root';

// Register the scene fonts by their real family names so the MP4 matches the
// live player: Caveat (board script), Geist (body), Bricolage Grotesque
// (explainer display), Archivo Black (marketing display). Weights are subset
// to what the design tokens actually use (tokens.ts TYPE_SCALE).
loadCaveat('normal', { weights: ['500', '600', '700'] });
loadGeist('normal', { weights: ['400', '500', '600', '700'] });
loadBricolage('normal', { weights: ['700', '800'] });
loadArchivoBlack('normal', { weights: ['400'] });

registerRoot(RemotionRoot);
