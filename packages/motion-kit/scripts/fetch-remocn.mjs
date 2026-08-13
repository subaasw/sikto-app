// Fetch remocn registry components into src/remocn/ (shadcn registry JSON:
// { files: [{ path, content }], dependencies, registryDependencies }).
import { mkdirSync, writeFileSync } from 'node:fs';
import { basename, join } from 'node:path';

const WANTED = [
  'blur-out-up',
  'staggered-fade-up',
  'tracking-in',
  'spring-scale-in',
  'rolling-number',
  'mesh-gradient-bg',
  'dynamic-grid',
  'confetti',
];
const outDir = new URL('../src/remocn/', import.meta.url).pathname;
mkdirSync(outDir, { recursive: true });

const seen = new Set();
const npmDeps = new Set();
async function fetchItem(name) {
  if (seen.has(name)) return;
  seen.add(name);
  const res = await fetch(`https://remocn.dev/r/${name}.json`);
  if (!res.ok) throw new Error(`${name}: HTTP ${res.status}`);
  const item = await res.json();
  for (const dep of item.registryDependencies ?? []) await fetchItem(dep.replace(/^@remocn\//, ''));
  for (const dep of item.dependencies ?? []) npmDeps.add(dep);
  for (const f of item.files ?? []) {
    // registry paths nest each component as <name>/index.tsx — flatten to <name>.tsx
    const base = basename(f.path);
    const out = base.startsWith('index.') ? `${name}${base.slice('index'.length)}` : base;
    writeFileSync(join(outDir, out), f.content);
    console.log(`wrote src/remocn/${out}`);
  }
}
for (const name of WANTED) await fetchItem(name);
if (npmDeps.size) console.log('\nnpm deps needed:', [...npmDeps].join(' '));
