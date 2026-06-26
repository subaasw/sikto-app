// Child worker that renders ONE still (PNG) of a single scene from the Lesson
// composition — used by the API's Vision QA pass to inspect a scene's layout.
// Slices the document to the requested scene, then renders a representative
// (mid-duration) frame. Mirrors scene-worker.mjs's bundling so the look matches.
import { mkdirSync, mkdtempSync, readFileSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { parseArgs } from 'node:util';

const { values } = parseArgs({
  options: {
    entry: { type: 'string' },
    props: { type: 'string' },
    out: { type: 'string' },
    id: { type: 'string' },
    scene: { type: 'string' },
  },
});

const { bundle } = await import('@remotion/bundler');
const { renderStill, selectComposition } = await import('@remotion/renderer');

const HERE = dirname(fileURLToPath(import.meta.url));
const SCENE_KIT = resolve(HERE, '../../../../packages/scene-kit/src/index.ts');

const inputProps = JSON.parse(readFileSync(values.props, 'utf8'));

// Render just the requested scene so the still's frame mapping is trivial.
if (values.scene && inputProps.document?.scenes) {
  const only = inputProps.document.scenes.filter((s) => s.id === values.scene);
  if (only.length) inputProps.document = { ...inputProps.document, scenes: only };
}

// Same manim-clip handling as the video worker, so a scene using staticFile() renders.
let publicDir;
const clips = inputProps.manim_clips || {};
if (Object.keys(clips).length) {
  publicDir = mkdtempSync(join(tmpdir(), 'sikto-public-'));
  mkdirSync(join(publicDir, 'manim'), { recursive: true });
  for (const id of Object.keys(clips)) {
    const m = /^data:video\/mp4;base64,(.+)$/s.exec(clips[id] ?? '');
    if (!m) continue;
    const rel = `manim/${id}.mp4`;
    writeFileSync(join(publicDir, rel), Buffer.from(m[1], 'base64'));
    clips[id] = rel;
  }
  inputProps.manim_clips = clips;
}

const serveUrl = await bundle({
  entryPoint: values.entry,
  publicDir,
  webpackOverride: (config) => ({
    ...config,
    resolve: {
      ...config.resolve,
      alias: { ...(config.resolve?.alias ?? {}), '@sikto/scene-kit$': SCENE_KIT },
    },
  }),
});
const composition = await selectComposition({ serveUrl, id: values.id, inputProps });
const frame = Math.max(0, Math.floor((composition.durationInFrames - 1) / 2));

await renderStill({ serveUrl, composition, output: values.out, frame, inputProps });
