// Render a single still PNG of the Lesson composition for eyeballing scenes.
// Usage: node still.mjs --entry <index.ts> --props <props.json> --out <png> --frame <n>
import { readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { parseArgs } from 'node:util';

const { values } = parseArgs({
  options: {
    entry: { type: 'string' },
    props: { type: 'string' },
    out: { type: 'string' },
    id: { type: 'string' },
    frame: { type: 'string' },
  },
});

const { bundle } = await import('@remotion/bundler');
const { renderStill, selectComposition } = await import('@remotion/renderer');

const HERE = dirname(fileURLToPath(import.meta.url));
const SCENE_KIT = resolve(HERE, '../../../packages/scene-kit/src/index.ts');
const MOTION_KIT = resolve(HERE, '../../../packages/motion-kit/src/index.ts');

const inputProps = JSON.parse(readFileSync(values.props, 'utf8'));
const serveUrl = await bundle({
  entryPoint: values.entry,
  webpackOverride: (config) => ({
    ...config,
    resolve: {
      ...config.resolve,
      alias: { ...(config.resolve?.alias ?? {}), '@sikto/scene-kit$': SCENE_KIT, '@sikto/motion-kit$': MOTION_KIT },
    },
  }),
});
const composition = await selectComposition({ serveUrl, id: values.id ?? 'Lesson', inputProps });
await renderStill({
  serveUrl,
  composition,
  output: values.out,
  frame: Number(values.frame ?? 80),
  inputProps,
});
console.log('wrote', values.out);
