// Child render worker for the declarative Lesson composition. Bundles the fixed
// Remotion project and renders the "Lesson" composition with the SceneDocument
// (plus audio / manim clip props) supplied as inputProps.
//
// Requires Remotion to be installed (remotion, @remotion/bundler, @remotion/renderer).
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
  },
});

const { bundle } = await import('@remotion/bundler');
const { renderMedia, selectComposition } = await import('@remotion/renderer');

// The shared scene renderer ships TS source. Point the bundler at the source dir
// (not the node_modules symlink) so Remotion's esbuild loader transpiles it —
// the loader excludes node_modules, which would otherwise choke on the .ts files.
const HERE = dirname(fileURLToPath(import.meta.url));
const SCENE_KIT = resolve(HERE, '../../../../packages/scene-kit/src/index.ts');

const inputProps = JSON.parse(readFileSync(values.props, 'utf8'));

// Manim clips arrive as base64 data-URLs, but <OffthreadVideo> proxies its src
// as a URL query param — a multi-MB data-URL overflows it (HTTP 431). So write
// each clip to a public dir and hand the composition a staticFile-relative path.
let publicDir;
const clips = inputProps.manim_clips || {};
const clipIds = Object.keys(clips);
if (clipIds.length) {
  publicDir = mkdtempSync(join(tmpdir(), 'sikto-public-'));
  mkdirSync(join(publicDir, 'manim'), { recursive: true });
  for (const id of clipIds) {
    const m = /^data:video\/mp4;base64,(.+)$/s.exec(clips[id] ?? '');
    if (!m) continue;
    const rel = `manim/${id}.mp4`;
    writeFileSync(join(publicDir, rel), Buffer.from(m[1], 'base64'));
    clips[id] = rel; // the Lesson resolves this via staticFile()
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

await renderMedia({
  serveUrl,
  composition,
  codec: 'h264',
  outputLocation: values.out,
  inputProps,
});
