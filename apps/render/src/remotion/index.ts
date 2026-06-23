import { loadFont as loadCaveat } from '@remotion/google-fonts/Caveat';
import { loadFont as loadGeist } from '@remotion/google-fonts/Geist';
import { registerRoot } from 'remotion';
import { RemotionRoot } from './Root';

// Register the scene fonts by their real family names ("Caveat" for hand-drawn
// headings, "Geist" for body) so the MP4 matches the live player. Without this
// Remotion rendered headings in a system fallback.
loadCaveat();
loadGeist();

registerRoot(RemotionRoot);
