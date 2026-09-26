// DATA-TRUTH auditor 2 (copy into ui/test/ of a clone, then: node ui/test/resolve_beats.mjs): resolve every beat headline + caption against the committed JSON
import fs from 'node:fs';
import path from 'node:path';
import zlib from 'node:zlib';
import { fileURLToPath } from 'node:url';
import * as fmt from '../lib/format.js';
import { sourcesFor, resolveCaption, placeholders, evalFact } from '../panels/more.js';
const UI = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const rd = (p) => { const f = path.join(UI, 'data', p); if (fs.existsSync(f)) return JSON.parse(fs.readFileSync(f, 'utf8')); if (fs.existsSync(f + '.gz')) return JSON.parse(zlib.gunzipSync(fs.readFileSync(f + '.gz')).toString()); return null; };
const src = (k) => k === 'p1meta' ? 'p1/meta.json' : k === 'p2index' ? 'p2/index.json' : k === 'engine' ? 'engine.json' : k === 'p1days' ? 'p1/days/index.json' : k === 'p1cal' ? 'p1/days/calendar.json' : k.startsWith('p1:') ? `p1/${k.slice(3)}.json` : k.startsWith('p2:') ? `p2/${k.slice(3)}.json` : null;
const beats = rd('beats.json').beats;
const topology = rd('topology.json');
for (const b of beats) {
  const keys = sourcesFor([b.caption, b.headline || '']);
  const S = { topology };
  for (const k of keys) if (k !== 'topology') S[k] = rd(src(k));
  console.log(`\n### ${b.id} (${b.t0}-${b.t1}) ${b.title} [${b.label}]  link=${b.link}`);
  console.log('HEADLINE: ' + resolveCaption(b.headline || '', S, fmt, { html: false }));
  console.log('CAPTION : ' + resolveCaption(b.caption, S, fmt, { html: false }));
  const names = [...new Set([...placeholders(b.headline||''), ...placeholders(b.caption)].filter(p => p.name).map(p => p.name))];
  for (const n of names) {
    const parts = evalFact(n, S);
    console.log(`   {{${n}}} = ` + (parts ? parts.map(p => typeof p === 'string' ? JSON.stringify(p) : `<${JSON.stringify(p.v)} ${p.label}${p.cite ? ' | ' + String(p.cite).slice(0,110) : ''}>`).join(' ') : 'NULL (not built yet)'));
  }
}
