// Child render worker. Runs in its own process (sandbox), bundles the workdir's
// Remotion project and renders the composition to the --out path.
//
// Requires Remotion to be installed to actually run:
//   pnpm --filter render add remotion @remotion/bundler @remotion/renderer
// Until then this file is only invoked by the real subprocess executor, never by tests
// (the RemotionRunner tests inject a stub executor).
import { parseArgs } from 'node:util';
import { join } from 'node:path';

const { values } = parseArgs({
  options: {
    workdir: { type: 'string' },
    composition: { type: 'string' },
    out: { type: 'string' },
  },
});

const { bundle } = await import('@remotion/bundler');
const { renderMedia, selectComposition } = await import('@remotion/renderer');

const serveUrl = await bundle({ entryPoint: join(values.workdir, 'index.ts') });
const composition = await selectComposition({ serveUrl, id: values.composition });
await renderMedia({
  serveUrl,
  composition,
  codec: 'h264',
  outputLocation: values.out,
});
