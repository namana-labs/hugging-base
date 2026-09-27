#!/usr/bin/env node
// ui/story/dev-b-fixtures/make-fixtures.mjs (UI-B, DEV ONLY; delete this whole folder, and ui/story/dev-b.html, at
// integration). Makes dev-b.html run on the REAL files before they are merged into this worktree: byte copies from
// the sibling worktrees (read-only there), plus routes.json for the harness:
//   ENGINE  ui/data/story/index.json (the real catalogue), a few p1/extras/*.json.gz, p1/variants/fleet=192/meta.json,
//           p1/worker_kill.json, p3/covert.json
//   PLANNER ui/data/p2/planner.json, ui/lib/planner.js (-> ./planner.js, loaded through ctx.devPlannerLib)
// routes.json: files {path under ui/data: url relative to dev-b.html} for the copies; absent [paths the catalogue
// names that are neither committed here nor copied] so the harness answers 404 without a request (the page shows
// "not built yet"). Run: node ui/story/dev-b-fixtures/make-fixtures.mjs   (HB_ENGINE / HB_PLANNER override)
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(HERE, '../../..');
const DATA = path.join(ROOT, 'ui/data');
const ENGINE = process.env.HB_ENGINE || 'C:/w/engine';
const PLANNER = process.env.HB_PLANNER || 'C:/w/planner';
const files = {};
function copy(src, rel, as = rel) {
  const dst = path.join(HERE, as);
  fs.mkdirSync(path.dirname(dst), { recursive: true });
  fs.copyFileSync(src, dst);
  if (rel) files[rel] = `./dev-b-fixtures/${as}`;
  console.log('copied', as, fs.statSync(dst).size >> 10, 'KB');
}
const eng = (rel) => path.join(ENGINE, 'ui/data', rel);

copy(eng('story/index.json'), 'story/index.json');
copy(path.join(PLANNER, 'ui/data/p2/planner.json'), 'p2/planner.json');
copy(path.join(PLANNER, 'ui/lib/planner.js'), null, 'planner.js');
const EXTRAS = ['2026-08-23_none', '2026-08-23_naive', '2026-08-23_aware', '2026-08-23_aware_faults', '2026-08-23_aware_worker_kill',
  '2026-08-23_naive_fleet=192', '2026-08-23_aware_fleet=192', '2026-07-22_none', '2026-07-22_naive', '2026-07-22_aware'];
for (const e of EXTRAS) copy(eng(`p1/extras/${e}.json.gz`), `p1/extras/${e}.json.gz`);
copy(eng('p1/variants/fleet=192/meta.json'), 'p1/variants/fleet=192/meta.json');
// byte-identical to Michael's committed originals (ENGINE copies them): route there instead of copying 2 MB
files['p1/worker_kill.json'] = '../../mpalacios/out/p1/worker_kill.json';
files['p3/covert.json'] = '../../mpalacios/out/p3/covert.json';

const cat = JSON.parse(fs.readFileSync(path.join(HERE, 'story/index.json'), 'utf8'));
const named = new Set();
for (const s of cat.scenarios) for (const p of [s.meta, s.branch, s.extras, s.attack]) if (p) named.add(p);
const absent = [...named].filter((p) => !files[p] && !fs.existsSync(path.join(DATA, p))).sort();
fs.writeFileSync(path.join(HERE, 'routes.json'), JSON.stringify({ note: 'UI-B dev harness routes (make-fixtures.mjs); delete at integration', files, absent }, null, 1));
console.log('routes.json:', Object.keys(files).length, 'copied paths,', absent.length, 'absent paths');
